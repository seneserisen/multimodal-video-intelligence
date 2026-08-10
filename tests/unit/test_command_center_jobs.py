from __future__ import annotations

import threading
import time
from collections.abc import Callable
from pathlib import Path

import pytest
from video_intelligence.command_center.jobs import (
    JobCapacityError,
    JobManager,
    JobStateError,
    JobStatus,
)
from video_intelligence.media import MediaProbeCancelled, MediaProbeResult, MediaStream


def successful_report(path: Path, _cancellation_requested: Callable[[], bool]) -> MediaProbeResult:
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


def test_successful_job_keeps_report_but_deletes_uploaded_media(tmp_path: Path) -> None:
    manager = JobManager(tmp_path / "jobs", processor=successful_report)
    _job, upload_path = manager.reserve("a" * 24, "authorized.mp4")
    upload_path.write_bytes(b"temporary-media")

    manager.submit("a" * 24)
    wait_for_terminal(manager, "a" * 24)
    completed = manager.get("a" * 24)

    assert completed.status == JobStatus.SUCCEEDED
    assert completed.report is not None
    assert completed.report.path == "authorized.mp4"
    assert not upload_path.parent.exists()
    assert manager.counts() == (0, 1, 0)
    manager.remove("a" * 24)
    assert manager.list() == []
    manager.shutdown()


def test_unexpected_processor_failure_is_safe_and_cleans_up(tmp_path: Path) -> None:
    def fail(_path: Path, _cancellation_requested: Callable[[], bool]) -> MediaProbeResult:
        raise RuntimeError("private implementation detail")

    manager = JobManager(tmp_path / "jobs", processor=fail)
    _job, upload_path = manager.reserve("b" * 24, "authorized.mp4")
    upload_path.write_bytes(b"temporary-media")

    manager.submit("b" * 24)
    wait_for_terminal(manager, "b" * 24)
    failed = manager.get("b" * 24)

    assert failed.status == JobStatus.FAILED
    assert failed.error is not None
    assert "private implementation detail" not in failed.error.message
    assert not upload_path.parent.exists()
    assert manager.counts() == (0, 0, 1)
    manager.shutdown()


def test_queued_job_can_be_cancelled_and_removed(tmp_path: Path) -> None:
    first_started = threading.Event()
    release_first = threading.Event()

    def blocking_report(path: Path, cancellation_requested: Callable[[], bool]) -> MediaProbeResult:
        if path.parent.name == "c" * 24:
            first_started.set()
            assert release_first.wait(timeout=2)
        return successful_report(path, cancellation_requested)

    manager = JobManager(tmp_path / "jobs", processor=blocking_report, max_workers=1)
    for job_id in ("c" * 24, "d" * 24):
        _job, upload_path = manager.reserve(job_id, "authorized.mp4")
        upload_path.write_bytes(b"temporary-media")
        manager.submit(job_id)

    assert first_started.wait(timeout=2)
    cancelled = manager.cancel("d" * 24)
    assert cancelled.status == JobStatus.CANCELLED
    assert not (tmp_path / "jobs" / ("d" * 24)).exists()
    manager.remove("d" * 24)

    with pytest.raises(JobStateError):
        manager.remove("c" * 24)
    release_first.set()
    wait_for_terminal(manager, "c" * 24)
    manager.shutdown()


def test_running_job_is_cooperatively_cancelled_and_cleaned(tmp_path: Path) -> None:
    started = threading.Event()

    def cancellable_report(
        _path: Path, cancellation_requested: Callable[[], bool]
    ) -> MediaProbeResult:
        started.set()
        while not cancellation_requested():
            time.sleep(0.01)
        raise MediaProbeCancelled

    manager = JobManager(tmp_path / "jobs", processor=cancellable_report)
    _job, upload_path = manager.reserve("e" * 24, "authorized.mp4")
    upload_path.write_bytes(b"temporary-media")
    manager.submit("e" * 24)

    assert started.wait(timeout=2)
    requested = manager.cancel("e" * 24)
    assert requested.cancellation_requested is True
    wait_for_terminal(manager, "e" * 24)

    cancelled = manager.get("e" * 24)
    assert cancelled.status == JobStatus.CANCELLED
    assert not upload_path.parent.exists()
    manager.shutdown()


def test_active_job_capacity_is_bounded(tmp_path: Path) -> None:
    manager = JobManager(tmp_path / "jobs", processor=successful_report, max_active_jobs=2)
    manager.reserve("f" * 24, "first.mp4")
    manager.reserve("1" * 24, "second.mp4")

    with pytest.raises(JobCapacityError, match="active job limit"):
        manager.reserve("2" * 24, "third.mp4")

    manager.shutdown()
