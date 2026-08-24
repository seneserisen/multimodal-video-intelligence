from __future__ import annotations

import json
import zipfile
from datetime import UTC, datetime
from pathlib import Path

import pytest
from video_intelligence.command_center.backup import backup_data, restore_data
from video_intelligence.command_center.jobs import JobStatus, ProcessingJob
from video_intelligence.command_center.store import JobStore


def test_backup_and_restore_preserve_database_media_and_relocate_paths(tmp_path: Path) -> None:
    source = tmp_path / "source-data"
    media = source / "media" / ("a" * 24) / "input.mp4"
    media.parent.mkdir(parents=True)
    media.write_bytes(b"authorized-test-media")
    now = datetime.now(UTC)
    job = ProcessingJob(
        job_id="a" * 24,
        status=JobStatus.SUCCEEDED,
        filename="authorized.mp4",
        content_sha256="b" * 64,
        created_at=now,
        updated_at=now,
        progress=1,
        message="complete",
        media_retained=True,
    )
    JobStore(source / "jobs.sqlite3").save(job, media)

    archive = backup_data(source, tmp_path / "backups")
    restored = restore_data(archive, tmp_path / "restored-data")

    loaded = JobStore(restored / "jobs.sqlite3").load()
    assert len(loaded) == 1
    restored_job, restored_media = loaded[0]
    assert restored_job.job_id == job.job_id
    assert restored_media == restored / "media" / job.job_id / "input.mp4"
    assert restored_media.read_bytes() == b"authorized-test-media"


def test_restore_rejects_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "unsafe.zip"
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr(
            "manifest.json",
            json.dumps({"format": "mvi-local-backup", "format_version": 1}),
        )
        bundle.writestr("../outside.txt", "unsafe")

    with pytest.raises(ValueError, match="unsafe path"):
        restore_data(archive, tmp_path / "data")
    assert not (tmp_path / "outside.txt").exists()
