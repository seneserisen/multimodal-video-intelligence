from __future__ import annotations

import threading
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path

import pytest
from video_intelligence.command_center.jobs import (
    DuplicateMediaError,
    JobCapacityError,
    JobManager,
    JobOperation,
    JobStage,
    JobStateError,
    JobStatus,
    ProcessingJob,
    ProcessingOutput,
)
from video_intelligence.command_center.store import JobStore
from video_intelligence.media import MediaProbeCancelled, MediaProbeResult, MediaStream
from video_intelligence.models import EvidenceItem
from video_intelligence.transcription import TranscriptionResult

HASH_A = "a" * 64
HASH_B = "b" * 64


def successful_report(path: Path) -> MediaProbeResult:
    assert path.exists()
    return MediaProbeResult(
        path=str(path),
        file_size_bytes=path.stat().st_size,
        format_names=["mp4"],
        duration_ms=1_000,
        streams=[
            MediaStream(
                index=0,
                stream_type="video",
                codec_name="h264",
                width=320,
                height=180,
            )
        ],
    )


def successful_processor(
    path: Path,
    _job: ProcessingJob,
    _cancellation_requested: Callable[[], bool],
    progress: Callable[[JobStage, float, str], None],
) -> ProcessingOutput:
    progress(JobStage.VALIDATION, 0.5, "testing")
    return ProcessingOutput(report=successful_report(path))


def wait_for_terminal(manager: JobManager, job_id: str) -> None:
    deadline = time.monotonic() + 2
    while manager.get(job_id).status not in {
        JobStatus.SUCCEEDED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
    }:
        if time.monotonic() >= deadline:
            pytest.fail("job did not reach a terminal state")
        time.sleep(0.01)


def test_successful_job_is_durable_until_explicit_removal(tmp_path: Path) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    manager = JobManager(tmp_path / "media", processor=successful_processor, store=store)
    _job, upload_path = manager.reserve("a" * 24, "authorized.mp4")
    upload_path.write_bytes(b"authorized-media")

    manager.submit("a" * 24, content_sha256=HASH_A)
    wait_for_terminal(manager, "a" * 24)
    completed = manager.get("a" * 24)

    assert completed.status == JobStatus.SUCCEEDED
    assert completed.report is not None
    assert completed.report.path == "authorized.mp4"
    assert completed.media_retained is True
    assert upload_path.exists()
    assert manager.counts() == (0, 1, 0)
    manager.shutdown()

    reopened = JobManager(tmp_path / "media", processor=successful_processor, store=store)
    assert reopened.get("a" * 24).status == JobStatus.SUCCEEDED
    reopened.remove("a" * 24)
    assert reopened.list() == []
    assert not upload_path.parent.exists()
    reopened.shutdown()


def test_unexpected_processor_failure_is_safe_and_retryable(tmp_path: Path) -> None:
    def fail(
        _path: Path,
        _job: ProcessingJob,
        _cancellation_requested: Callable[[], bool],
        _progress: Callable[[JobStage, float, str], None],
    ) -> ProcessingOutput:
        raise RuntimeError("private implementation detail")

    manager = JobManager(tmp_path / "media", processor=fail)
    _job, upload_path = manager.reserve("b" * 24, "authorized.mp4")
    upload_path.write_bytes(b"authorized-media")

    manager.submit("b" * 24, content_sha256=HASH_B)
    wait_for_terminal(manager, "b" * 24)
    failed = manager.get("b" * 24)

    assert failed.status == JobStatus.FAILED
    assert failed.error is not None
    assert "private implementation detail" not in failed.error.message
    assert upload_path.exists()
    assert manager.counts() == (0, 0, 1)
    manager.shutdown()


def test_queued_job_can_be_cancelled_retried_and_removed(tmp_path: Path) -> None:
    first_started = threading.Event()
    release_first = threading.Event()

    def blocking_processor(
        path: Path,
        _job: ProcessingJob,
        _cancellation_requested: Callable[[], bool],
        _progress: Callable[[JobStage, float, str], None],
    ) -> ProcessingOutput:
        if path.parent.name == "c" * 24:
            first_started.set()
            assert release_first.wait(timeout=2)
        return ProcessingOutput(report=successful_report(path))

    manager = JobManager(tmp_path / "media", processor=blocking_processor, max_workers=1)
    for job_id, digest in (("c" * 24, HASH_A), ("d" * 24, HASH_B)):
        _job, upload_path = manager.reserve(job_id, "authorized.mp4")
        upload_path.write_bytes(job_id.encode())
        manager.submit(job_id, content_sha256=digest)

    assert first_started.wait(timeout=2)
    cancelled = manager.cancel("d" * 24)
    assert cancelled.status == JobStatus.CANCELLED
    assert (tmp_path / "media" / ("d" * 24)).exists()
    retried = manager.retry("d" * 24)
    assert retried.status == JobStatus.QUEUED

    with pytest.raises(JobStateError):
        manager.remove("c" * 24)
    release_first.set()
    wait_for_terminal(manager, "c" * 24)
    wait_for_terminal(manager, "d" * 24)
    manager.shutdown()


def test_running_job_is_cooperatively_cancelled(tmp_path: Path) -> None:
    started = threading.Event()

    def cancellable_processor(
        _path: Path,
        _job: ProcessingJob,
        cancellation_requested: Callable[[], bool],
        _progress: Callable[[JobStage, float, str], None],
    ) -> ProcessingOutput:
        started.set()
        while not cancellation_requested():
            time.sleep(0.01)
        raise MediaProbeCancelled

    manager = JobManager(tmp_path / "media", processor=cancellable_processor)
    _job, upload_path = manager.reserve("e" * 24, "authorized.mp4")
    upload_path.write_bytes(b"authorized-media")
    manager.submit("e" * 24, content_sha256=HASH_A)

    assert started.wait(timeout=2)
    requested = manager.cancel("e" * 24)
    assert requested.cancellation_requested is True
    wait_for_terminal(manager, "e" * 24)

    cancelled = manager.get("e" * 24)
    assert cancelled.status == JobStatus.CANCELLED
    assert upload_path.exists()
    manager.shutdown()


def test_active_job_capacity_and_duplicate_media_are_bounded(tmp_path: Path) -> None:
    manager = JobManager(
        tmp_path / "media",
        processor=successful_processor,
        max_active_jobs=2,
    )
    manager.reserve("f" * 24, "first.mp4")
    manager.reserve("1" * 24, "second.mp4")
    with pytest.raises(JobCapacityError, match="active job limit"):
        manager.reserve("2" * 24, "third.mp4")
    manager.fail_upload("f" * 24, "test cleanup")
    manager.fail_upload("1" * 24, "test cleanup")

    _job, first = manager.reserve("3" * 24, "first.mp4")
    first.write_bytes(b"same")
    manager.submit("3" * 24, content_sha256=HASH_A)
    wait_for_terminal(manager, "3" * 24)
    _job, duplicate = manager.reserve("4" * 24, "duplicate.mp4")
    duplicate.write_bytes(b"same")
    with pytest.raises(DuplicateMediaError) as caught:
        manager.submit("4" * 24, content_sha256=HASH_A)
    assert caught.value.existing_job_id == "3" * 24
    assert not duplicate.parent.exists()
    manager.shutdown()


def test_interrupted_job_recovers_and_transcript_edit_preserves_provenance(
    tmp_path: Path,
) -> None:
    store = JobStore(tmp_path / "jobs.sqlite3")
    media_path = tmp_path / "media" / ("5" * 24) / "input.mp4"
    media_path.parent.mkdir(parents=True)
    media_path.write_bytes(b"authorized-media")
    now = datetime.now(UTC)
    interrupted = ProcessingJob(
        job_id="5" * 24,
        status=JobStatus.RUNNING,
        stage=JobStage.TRANSCRIPTION,
        operations=[JobOperation.VALIDATE, JobOperation.TRANSCRIBE],
        filename="speech.mp4",
        content_sha256=HASH_A,
        created_at=now,
        updated_at=now,
        progress=0.7,
        message="interrupted",
        media_retained=True,
    )
    store.save(interrupted, media_path)

    def transcript_processor(
        path: Path,
        _job: ProcessingJob,
        _cancel: Callable[[], bool],
        _progress: Callable[[JobStage, float, str], None],
    ) -> ProcessingOutput:
        item = EvidenceItem(
            evidence_id="speech-000000",
            modality="speech",
            evidence_type="transcript_segment",
            start_ms=0,
            end_ms=1000,
            text="original",
            confidence=0.9,
            source_reference="speech.mp4",
            language="en",
            provider="fake-local",
            processing_version="1",
        )
        return ProcessingOutput(
            report=successful_report(path),
            transcription=TranscriptionResult(
                provider="fake-local",
                processing_version="1",
                language="en",
                language_confidence=0.95,
                evidence_items=[item],
            ),
        )

    manager = JobManager(tmp_path / "media", processor=transcript_processor, store=store)
    wait_for_terminal(manager, "5" * 24)
    recovered = manager.get("5" * 24)
    assert recovered.recovered_after_restart is True
    edited = manager.edit_transcript("5" * 24, "speech-000000", "corrected")
    assert edited.transcription is not None
    segment = edited.transcription.evidence_items[0]
    assert segment.text == "corrected"
    assert segment.attributes == {"original_text": "original", "user_edited": True}
    assert segment.provider == "fake-local"
    manager.shutdown()
