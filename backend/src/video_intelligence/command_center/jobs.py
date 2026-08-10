from __future__ import annotations

import shutil
import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from video_intelligence.errors import ErrorCode, StructuredError, VideoIntelligenceError
from video_intelligence.media import MediaProbeCancelled, MediaProbeResult, probe_media
from video_intelligence.models import SCHEMA_VERSION


class JobStatus(StrEnum):
    UPLOADING = "uploading"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


TERMINAL_STATUSES = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}


class ProcessingJob(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)

    schema_version: str = SCHEMA_VERSION
    job_id: str
    status: JobStatus
    filename: str
    created_at: datetime
    updated_at: datetime
    progress: float = Field(ge=0, le=1)
    message: str
    cancellation_requested: bool = False
    report: MediaProbeResult | None = None
    error: StructuredError | None = None


class ProcessingJobList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    jobs: list[ProcessingJob]


class JobProcessor(Protocol):
    def __call__(
        self, path: Path, cancellation_requested: Callable[[], bool]
    ) -> MediaProbeResult: ...


def process_media_job(path: Path, cancellation_requested: Callable[[], bool]) -> MediaProbeResult:
    return probe_media(path, cancellation_requested=cancellation_requested)


class JobNotFoundError(KeyError):
    pass


class JobCapacityError(RuntimeError):
    pass


class JobStateError(RuntimeError):
    pass


class JobManager:
    def __init__(
        self,
        root: Path,
        *,
        processor: JobProcessor = process_media_job,
        max_workers: int = 1,
        max_records: int = 50,
        max_active_jobs: int = 2,
    ) -> None:
        self.root = root
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        self.processor = processor
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

    def reserve(self, job_id: str, filename: str) -> tuple[ProcessingJob, Path]:
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
            job = ProcessingJob(
                job_id=job_id,
                status=JobStatus.UPLOADING,
                filename=filename,
                created_at=now,
                updated_at=now,
                progress=0,
                message="Uploading media.",
            )
            self._jobs[job_id] = job
            self._paths[job_id] = upload_path
            return job.model_copy(deep=True), upload_path

    def submit(self, job_id: str) -> ProcessingJob:
        with self._lock:
            job = self._require(job_id)
            if job.status != JobStatus.UPLOADING:
                raise JobStateError("only an uploaded job can be submitted")
            if job.cancellation_requested:
                self._set_cancelled(job)
                self._cleanup(job_id)
                return job.model_copy(deep=True)
            job.status = JobStatus.QUEUED
            job.progress = 0.1
            job.message = "Queued for local media validation."
            job.updated_at = datetime.now(UTC)
            self._futures[job_id] = self._executor.submit(self._process, job_id)
            return job.model_copy(deep=True)

    def fail_upload(self, job_id: str, message: str) -> ProcessingJob:
        with self._lock:
            job = self._require(job_id)
            job.status = JobStatus.FAILED
            job.progress = 1
            job.message = "Upload failed."
            job.error = StructuredError(
                code=ErrorCode.UNAVAILABLE_MEDIA,
                message=message,
                safe_recovery_action="Retry with a supported local media file.",
            )
            job.updated_at = datetime.now(UTC)
            self._cleanup(job_id)
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
                self._cleanup(job_id)
            else:
                job.message = "Cancellation requested; waiting for the current local probe."
            return job.model_copy(deep=True)

    def remove(self, job_id: str) -> None:
        with self._lock:
            job = self._require(job_id)
            if job.status not in TERMINAL_STATUSES:
                raise JobStateError("active jobs must be cancelled before removal")
            future = self._futures.pop(job_id, None)
            if future is not None:
                future.cancel()
            self._cleanup(job_id)
            del self._jobs[job_id]
            self._paths.pop(job_id, None)

    def shutdown(self) -> None:
        with self._lock:
            self._closed = True
            for job in self._jobs.values():
                if job.status not in TERMINAL_STATUSES:
                    job.cancellation_requested = True
        self._executor.shutdown(wait=True, cancel_futures=True)
        with self._lock:
            for job_id in list(self._paths):
                self._cleanup(job_id)
            self._futures.clear()

    def _process(self, job_id: str) -> None:
        with self._lock:
            job = self._require(job_id)
            if job.cancellation_requested:
                self._set_cancelled(job)
                self._cleanup(job_id)
                return
            job.status = JobStatus.RUNNING
            job.progress = 0.5
            job.message = "Inspecting streams, duration, dimensions, and codecs."
            job.updated_at = datetime.now(UTC)
            path = self._paths[job_id]
        try:
            report = self.processor(path, lambda: self._cancellation_requested(job_id))
            report.path = job.filename
            with self._lock:
                job = self._require(job_id)
                if job.cancellation_requested:
                    self._set_cancelled(job)
                else:
                    job.status = JobStatus.SUCCEEDED if report.valid else JobStatus.FAILED
                    job.progress = 1
                    job.report = report
                    job.message = (
                        "Media validation completed."
                        if report.valid
                        else "Media validation completed with errors."
                    )
                    job.updated_at = datetime.now(UTC)
        except MediaProbeCancelled:
            with self._lock:
                job = self._require(job_id)
                self._set_cancelled(job)
        except VideoIntelligenceError as exc:
            with self._lock:
                job = self._require(job_id)
                job.status = JobStatus.CANCELLED if job.cancellation_requested else JobStatus.FAILED
                job.progress = 1
                job.message = "Media validation failed."
                job.error = None if job.cancellation_requested else exc.detail
                job.updated_at = datetime.now(UTC)
        except Exception:
            with self._lock:
                job = self._require(job_id)
                job.status = JobStatus.CANCELLED if job.cancellation_requested else JobStatus.FAILED
                job.progress = 1
                job.message = "Media validation failed safely."
                job.error = (
                    None
                    if job.cancellation_requested
                    else StructuredError(
                        code=ErrorCode.SCHEMA_VALIDATION_FAILURE,
                        message="The local media validator returned an unexpected result.",
                        safe_recovery_action="Inspect the command-center log and retry.",
                    )
                )
                job.updated_at = datetime.now(UTC)
        finally:
            with self._lock:
                self._cleanup(job_id)

    def _set_cancelled(self, job: ProcessingJob) -> None:
        job.status = JobStatus.CANCELLED
        job.progress = 1
        job.message = "Job cancelled; temporary media was removed."
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

    def _cleanup(self, job_id: str) -> None:
        path = self._paths.get(job_id)
        if path is None:
            return
        directory = path.parent.resolve()
        root = self.root.resolve()
        if directory.parent == root and directory.name == job_id:
            shutil.rmtree(directory, ignore_errors=True)
