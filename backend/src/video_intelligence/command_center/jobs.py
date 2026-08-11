from __future__ import annotations

import shutil
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from video_intelligence.command_center.store import JobStore
from video_intelligence.errors import ErrorCode, StructuredError, VideoIntelligenceError
from video_intelligence.media import MediaProbeCancelled, MediaProbeResult, probe_media
from video_intelligence.models import SCHEMA_VERSION
from video_intelligence.transcription import (
    AudioExtractor,
    TranscriptionCancelled,
    TranscriptionProvider,
    TranscriptionResult,
)


class JobStatus(StrEnum):
    UPLOADING = "uploading"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobOperation(StrEnum):
    VALIDATE = "validate"
    TRANSCRIBE = "transcribe"


class JobStage(StrEnum):
    UPLOAD = "upload"
    QUEUE = "queue"
    VALIDATION = "validation"
    AUDIO_EXTRACTION = "audio_extraction"
    TRANSCRIPTION = "transcription"
    COMPLETE = "complete"


TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}


class ProcessingJob(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    schema_version: str = SCHEMA_VERSION
    job_id: str = Field(pattern=r"^[0-9a-f]{24}$")
    status: JobStatus
    stage: JobStage = JobStage.UPLOAD
    operations: list[JobOperation] = Field(default_factory=lambda: [JobOperation.VALIDATE])
    filename: str
    content_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    created_at: datetime
    updated_at: datetime
    progress: float = Field(ge=0, le=1)
    message: str
    cancellation_requested: bool = False
    recovered_after_restart: bool = False
    media_retained: bool = False
    report: MediaProbeResult | None = None
    transcription: TranscriptionResult | None = None
    error: StructuredError | None = None


class ProcessingJobList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    jobs: list[ProcessingJob]


@dataclass(frozen=True)
class ProcessingOutput:
    report: MediaProbeResult
    transcription: TranscriptionResult | None = None


ProgressCallback = Callable[[JobStage, float, str], None]


class JobProcessor(Protocol):
    def __call__(
        self,
        path: Path,
        job: ProcessingJob,
        cancellation_requested: Callable[[], bool],
        progress: ProgressCallback,
    ) -> ProcessingOutput: ...


class MediaJobProcessor:
    def __init__(
        self,
        work_root: Path,
        *,
        transcription_provider: TranscriptionProvider | None = None,
        audio_extractor: AudioExtractor | None = None,
    ) -> None:
        self.work_root = work_root.resolve(strict=False)
        self.work_root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.transcription_provider = transcription_provider
        self.audio_extractor = audio_extractor or AudioExtractor()

    def __call__(
        self,
        path: Path,
        job: ProcessingJob,
        cancellation_requested: Callable[[], bool],
        progress: ProgressCallback,
    ) -> ProcessingOutput:
        report = job.report
        if report is None:
            progress(JobStage.VALIDATION, 0.25, "Validating media streams and limits.")
            report = probe_media(path, cancellation_requested=cancellation_requested)
            report.path = job.filename
        if not report.valid or JobOperation.TRANSCRIBE not in job.operations:
            return ProcessingOutput(report=report)
        if not any(stream.stream_type == "audio" for stream in report.streams):
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.MISSING_AUDIO,
                    message="The selected media has no audio stream to transcribe.",
                    safe_recovery_action="Use validation-only mode or select media with audio.",
                )
            )
        if self.transcription_provider is None:
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message="Local transcription is not configured.",
                    safe_recovery_action=(
                        "Configure a local Faster-Whisper model, then retry this job."
                    ),
                )
            )
        work_dir = self.work_root / job.job_id
        audio_path = work_dir / "audio.wav"
        try:
            progress(JobStage.AUDIO_EXTRACTION, 0.5, "Extracting bounded local audio.")
            self.audio_extractor.extract(path, audio_path, cancellation_requested)
            progress(JobStage.TRANSCRIPTION, 0.7, "Transcribing speech with the local model.")
            transcription = self.transcription_provider.transcribe(
                audio_path,
                source_reference=job.filename,
                cancellation_requested=cancellation_requested,
            )
            return ProcessingOutput(report=report, transcription=transcription)
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


class JobNotFoundError(KeyError):
    pass


class JobCapacityError(RuntimeError):
    pass


class JobStateError(RuntimeError):
    pass


class DuplicateMediaError(RuntimeError):
    def __init__(self, existing_job_id: str) -> None:
        super().__init__("media already exists")
        self.existing_job_id = existing_job_id


class JobManager:
    def __init__(
        self,
        root: Path,
        *,
        processor: JobProcessor,
        store: JobStore | None = None,
        max_workers: int = 1,
        max_records: int = 500,
        max_active_jobs: int = 2,
    ) -> None:
        self.root = root.resolve(strict=False)
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.processor = processor
        self.store = store
        self.max_records = max_records
        self.max_active_jobs = max_active_jobs
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="mvi-job",
        )
        self._jobs: dict[str, ProcessingJob] = {}
        self._paths: dict[str, Path] = {}
        self._futures: dict[str, Future[None]] = {}
        self._lock = threading.RLock()
        self._closed = False
        self._load_and_recover()

    def _load_and_recover(self) -> None:
        if self.store is None:
            return
        recover: list[str] = []
        for job, stored_media_path in self.store.load():
            media_path = (
                self.root / job.job_id / f"input{Path(job.filename).suffix.casefold()}"
            ).resolve(strict=False)
            if stored_media_path.resolve(strict=False) != media_path:
                job.recovered_after_restart = True
            self._jobs[job.job_id] = job
            self._paths[job.job_id] = media_path
            if job.status == JobStatus.UPLOADING:
                job.status = JobStatus.FAILED
                job.stage = JobStage.COMPLETE
                job.progress = 1
                job.message = "An interrupted upload was removed during recovery."
                job.error = StructuredError(
                    code=ErrorCode.UNAVAILABLE_MEDIA,
                    message="The upload did not complete before the previous process stopped.",
                    safe_recovery_action="Upload the authorized media again.",
                )
                job.updated_at = datetime.now(UTC)
                self._delete_media(job.job_id)
                self._persist(job.job_id)
            elif job.status not in TERMINAL_STATUSES:
                if media_path.is_file():
                    job.status = JobStatus.QUEUED
                    job.stage = JobStage.QUEUE
                    job.progress = min(job.progress, 0.1)
                    job.message = "Recovered after restart and queued for safe reprocessing."
                    job.cancellation_requested = False
                    job.recovered_after_restart = True
                    job.updated_at = datetime.now(UTC)
                    self._persist(job.job_id)
                    recover.append(job.job_id)
                else:
                    job.status = JobStatus.FAILED
                    job.stage = JobStage.COMPLETE
                    job.progress = 1
                    job.message = "Recovery failed because retained media is missing."
                    job.error = StructuredError(
                        code=ErrorCode.UNAVAILABLE_MEDIA,
                        message="The retained source media is no longer available.",
                        safe_recovery_action="Delete the job and upload the media again.",
                    )
                    job.updated_at = datetime.now(UTC)
                    self._persist(job.job_id)
        for job_id in recover:
            self._futures[job_id] = self._executor.submit(self._process, job_id)

    def reserve(
        self,
        job_id: str,
        filename: str,
        *,
        transcribe: bool = False,
    ) -> tuple[ProcessingJob, Path]:
        with self._lock:
            if self._closed:
                raise JobStateError("job manager is closed")
            if len(self._jobs) >= self.max_records:
                raise JobCapacityError("job record limit reached")
            active = sum(job.status not in TERMINAL_STATUSES for job in self._jobs.values())
            if active >= self.max_active_jobs:
                raise JobCapacityError("active job limit reached")
            if job_id in self._jobs:
                raise JobStateError("job ID already exists")
            now = datetime.now(UTC)
            directory = self.root / job_id
            directory.mkdir(mode=0o700)
            upload_path = directory / f"input{Path(filename).suffix.casefold()}"
            operations = [JobOperation.VALIDATE]
            if transcribe:
                operations.append(JobOperation.TRANSCRIBE)
            job = ProcessingJob(
                job_id=job_id,
                status=JobStatus.UPLOADING,
                operations=operations,
                filename=filename,
                created_at=now,
                updated_at=now,
                progress=0,
                message="Uploading authorized media.",
            )
            self._jobs[job_id] = job
            self._paths[job_id] = upload_path
            self._persist(job_id)
            return job.model_copy(deep=True), upload_path

    def submit(self, job_id: str, *, content_sha256: str) -> ProcessingJob:
        with self._lock:
            job = self._require(job_id)
            if job.status != JobStatus.UPLOADING:
                raise JobStateError("only an uploaded job can be submitted")
            duplicate = self._duplicate_job_id(content_sha256, job_id)
            if duplicate is not None:
                self._discard(job_id)
                raise DuplicateMediaError(duplicate)
            job.content_sha256 = content_sha256
            job.media_retained = True
            job.status = JobStatus.QUEUED
            job.stage = JobStage.QUEUE
            job.progress = 0.1
            job.message = "Queued for durable local processing."
            job.updated_at = datetime.now(UTC)
            self._persist(job_id)
            self._futures[job_id] = self._executor.submit(self._process, job_id)
            return job.model_copy(deep=True)

    def fail_upload(self, job_id: str, message: str) -> ProcessingJob:
        with self._lock:
            job = self._require(job_id)
            job.status = JobStatus.FAILED
            job.stage = JobStage.COMPLETE
            job.progress = 1
            job.message = "Upload failed."
            job.error = StructuredError(
                code=ErrorCode.UNAVAILABLE_MEDIA,
                message=message,
                safe_recovery_action="Retry with a supported local media file.",
            )
            job.updated_at = datetime.now(UTC)
            self._delete_media(job_id)
            self._persist(job_id)
            return job.model_copy(deep=True)

    def get(self, job_id: str) -> ProcessingJob:
        with self._lock:
            return self._require(job_id).model_copy(deep=True)

    def list(self) -> list[ProcessingJob]:
        with self._lock:
            return [
                job.model_copy(deep=True)
                for job in sorted(
                    self._jobs.values(),
                    key=lambda item: item.created_at,
                    reverse=True,
                )
            ]

    def counts(self) -> tuple[int, int, int]:
        with self._lock:
            active = sum(job.status not in TERMINAL_STATUSES for job in self._jobs.values())
            succeeded = sum(job.status == JobStatus.SUCCEEDED for job in self._jobs.values())
            failed = sum(
                job.status in {JobStatus.FAILED, JobStatus.CANCELLED} for job in self._jobs.values()
            )
            return active, succeeded, failed

    def cancel(self, job_id: str) -> ProcessingJob:
        with self._lock:
            job = self._require(job_id)
            if job.status in TERMINAL_STATUSES:
                return job.model_copy(deep=True)
            job.cancellation_requested = True
            job.updated_at = datetime.now(UTC)
            if job.status in {JobStatus.UPLOADING, JobStatus.QUEUED}:
                self._set_cancelled(job)
                future = self._futures.get(job_id)
                if future is not None:
                    future.cancel()
            else:
                job.message = "Cancellation requested; stopping the active local stage."
            self._persist(job_id)
            return job.model_copy(deep=True)

    def retry(self, job_id: str) -> ProcessingJob:
        with self._lock:
            job = self._require(job_id)
            if job.status not in TERMINAL_STATUSES:
                raise JobStateError("only terminal jobs can be retried")
            path = self._paths[job_id]
            if not path.is_file():
                raise JobStateError("retained media is unavailable")
            job.status = JobStatus.QUEUED
            job.stage = JobStage.QUEUE
            job.progress = 0.1
            job.message = "Queued for retry."
            job.cancellation_requested = False
            job.error = None
            job.updated_at = datetime.now(UTC)
            self._persist(job_id)
            self._futures[job_id] = self._executor.submit(self._process, job_id)
            return job.model_copy(deep=True)

    def edit_transcript(self, job_id: str, evidence_id: str, text: str) -> ProcessingJob:
        cleaned = text.strip()
        if not cleaned or len(cleaned) > 20_000:
            raise JobStateError("transcript text must contain 1 to 20000 characters")
        with self._lock:
            job = self._require(job_id)
            if job.transcription is None:
                raise JobStateError("job has no transcript")
            for index, item in enumerate(job.transcription.evidence_items):
                if item.evidence_id != evidence_id:
                    continue
                attributes = dict(item.attributes)
                attributes.setdefault("original_text", item.text)
                attributes["user_edited"] = True
                job.transcription.evidence_items[index] = item.model_copy(
                    update={"text": cleaned, "attributes": attributes}
                )
                job.updated_at = datetime.now(UTC)
                job.message = "Transcript edit saved locally with original provenance."
                self._persist(job_id)
                return job.model_copy(deep=True)
            raise JobNotFoundError(evidence_id)

    def remove(self, job_id: str) -> None:
        with self._lock:
            job = self._require(job_id)
            if job.status not in TERMINAL_STATUSES:
                raise JobStateError("active jobs must be cancelled before removal")
            future = self._futures.pop(job_id, None)
            if future is not None:
                future.cancel()
            self._delete_media(job_id)
            del self._jobs[job_id]
            self._paths.pop(job_id, None)
            if self.store is not None:
                self.store.delete(job_id)

    def shutdown(self) -> None:
        with self._lock:
            self._closed = True
            for job in self._jobs.values():
                if job.status not in TERMINAL_STATUSES:
                    job.cancellation_requested = True
                    self._persist(job.job_id)
        self._executor.shutdown(wait=True, cancel_futures=True)
        with self._lock:
            self._futures.clear()

    def _process(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.cancellation_requested:
                if job is not None:
                    self._set_cancelled(job)
                    self._persist(job_id)
                return
            job.status = JobStatus.RUNNING
            job.message = "Starting durable local processing."
            job.updated_at = datetime.now(UTC)
            path = self._paths[job_id]
            snapshot = job.model_copy(deep=True)
            self._persist(job_id)
        try:
            output = self.processor(
                path,
                snapshot,
                lambda: self._cancellation_requested(job_id),
                lambda stage, value, message: self._progress(job_id, stage, value, message),
            )
            with self._lock:
                job = self._require(job_id)
                output.report.path = job.filename
                if job.cancellation_requested:
                    self._set_cancelled(job)
                else:
                    job.status = JobStatus.SUCCEEDED if output.report.valid else JobStatus.FAILED
                    job.stage = JobStage.COMPLETE
                    job.progress = 1
                    job.report = output.report
                    job.transcription = output.transcription
                    job.message = (
                        "Durable transcription completed."
                        if output.transcription is not None
                        else "Durable media validation completed."
                    )
                    job.updated_at = datetime.now(UTC)
                self._persist(job_id)
        except (MediaProbeCancelled, TranscriptionCancelled):
            with self._lock:
                job = self._require(job_id)
                self._set_cancelled(job)
                self._persist(job_id)
        except VideoIntelligenceError as exc:
            with self._lock:
                job = self._require(job_id)
                job.status = JobStatus.CANCELLED if job.cancellation_requested else JobStatus.FAILED
                job.stage = JobStage.COMPLETE
                job.progress = 1
                job.message = "Local processing failed."
                job.error = None if job.cancellation_requested else exc.detail
                job.updated_at = datetime.now(UTC)
                self._persist(job_id)
        except Exception:
            with self._lock:
                job = self._require(job_id)
                job.status = JobStatus.CANCELLED if job.cancellation_requested else JobStatus.FAILED
                job.stage = JobStage.COMPLETE
                job.progress = 1
                job.message = "Local processing failed safely."
                job.error = (
                    None
                    if job.cancellation_requested
                    else StructuredError(
                        code=ErrorCode.SCHEMA_VALIDATION_FAILURE,
                        message="The local processing pipeline returned an unexpected result.",
                        safe_recovery_action="Inspect the local log and retry.",
                    )
                )
                job.updated_at = datetime.now(UTC)
                self._persist(job_id)

    def _progress(self, job_id: str, stage: JobStage, value: float, message: str) -> None:
        with self._lock:
            job = self._require(job_id)
            job.stage = stage
            job.progress = value
            job.message = message
            job.updated_at = datetime.now(UTC)
            self._persist(job_id)

    def _set_cancelled(self, job: ProcessingJob) -> None:
        job.status = JobStatus.CANCELLED
        job.stage = JobStage.COMPLETE
        job.progress = 1
        job.message = "Job cancelled; retained source remains until deletion."
        job.updated_at = datetime.now(UTC)

    def _require(self, job_id: str) -> ProcessingJob:
        try:
            return self._jobs[job_id]
        except KeyError as exc:
            raise JobNotFoundError(job_id) from exc

    def _cancellation_requested(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            return job is None or job.cancellation_requested or self._closed

    def _persist(self, job_id: str) -> None:
        if self.store is not None:
            self.store.save(self._jobs[job_id], self._paths[job_id])

    def _duplicate_job_id(self, content_sha256: str, job_id: str) -> str | None:
        if self.store is not None:
            return self.store.duplicate_job_id(content_sha256, exclude_job_id=job_id)
        for existing in self._jobs.values():
            if existing.job_id != job_id and existing.content_sha256 == content_sha256:
                return existing.job_id
        return None

    def _discard(self, job_id: str) -> None:
        self._delete_media(job_id)
        self._jobs.pop(job_id, None)
        self._paths.pop(job_id, None)
        if self.store is not None:
            self.store.delete(job_id)

    def _delete_media(self, job_id: str) -> None:
        path = self._paths.get(job_id)
        if path is None:
            return
        directory = path.parent.resolve(strict=False)
        root = self.root.resolve(strict=False)
        if directory.parent == root and directory.name == job_id:
            shutil.rmtree(directory, ignore_errors=True)
