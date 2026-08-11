from __future__ import annotations

import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

from video_intelligence import __version__
from video_intelligence.command_center.data import prepare_data_dir
from video_intelligence.command_center.store import JobStore

MAX_RESTORE_BYTES = 100 * 1024**3
MAX_RESTORE_FILES = 100_000


def backup_data(data_dir: Path, output_dir: Path) -> Path:
    source = prepare_data_dir(data_dir)
    destination = output_dir.resolve(strict=False)
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    archive = destination / f"mvi-backup-{stamp}.zip"
    with tempfile.TemporaryDirectory(prefix="mvi-backup-") as temporary:
        staging = Path(temporary) / "data"
        staging.mkdir()
        database = source / "jobs.sqlite3"
        if database.exists():
            JobStore(database).backup_to(staging / "jobs.sqlite3")
        media = source / "media"
        if media.exists():
            shutil.copytree(media, staging / "media")
        manifest = {
            "format": "mvi-local-backup",
            "format_version": 1,
            "application_version": __version__,
            "created_at": datetime.now(UTC).isoformat(),
        }
        (Path(temporary) / "manifest.json").write_text(
            json.dumps(manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        with zipfile.ZipFile(archive, "x", compression=zipfile.ZIP_DEFLATED) as bundle:
            bundle.write(Path(temporary) / "manifest.json", "manifest.json")
            for path in sorted(staging.rglob("*")):
                if path.is_file():
                    bundle.write(path, path.relative_to(Path(temporary)).as_posix())
    return archive


def _validated_members(bundle: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    members = bundle.infolist()
    if len(members) > MAX_RESTORE_FILES:
        raise ValueError("Backup contains too many files.")
    total = 0
    for member in members:
        if "\\" in member.filename or ":" in member.filename:
            raise ValueError("Backup contains an unsafe path.")
        path = PurePosixPath(member.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("Backup contains an unsafe path.")
        if path.parts[0] not in {"manifest.json", "data"}:
            raise ValueError("Backup contains an unexpected file.")
        if (member.external_attr >> 16) & 0o170000 == 0o120000:
            raise ValueError("Backup contains an unsupported symbolic link.")
        total += member.file_size
        if total > MAX_RESTORE_BYTES:
            raise ValueError("Backup exceeds the restore size limit.")
    return members


def restore_data(archive: Path, data_dir: Path) -> Path:
    source = archive.resolve(strict=True)
    target = prepare_data_dir(data_dir)
    with tempfile.TemporaryDirectory(prefix="mvi-restore-") as temporary:
        staging = Path(temporary)
        with zipfile.ZipFile(source) as bundle:
            members = _validated_members(bundle)
            bundle.extractall(staging, members=members)
        manifest_path = staging / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("format") != "mvi-local-backup" or manifest.get("format_version") != 1:
            raise ValueError("Backup manifest is not supported.")
        restored = staging / "data"
        restored_database = restored / "jobs.sqlite3"
        if restored_database.exists():
            with closing(sqlite3.connect(restored_database)) as connection:
                integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or integrity[0] != "ok":
                raise ValueError("Backup database failed its integrity check.")
            JobStore(restored_database).load()
        replacement = target.with_name(f"{target.name}.restore-{os.getpid()}")
        if replacement.exists():
            shutil.rmtree(replacement)
        shutil.copytree(restored, replacement)
        previous = target.with_name(f"{target.name}.before-restore-{os.getpid()}")
        if previous.exists():
            shutil.rmtree(previous)
        os.replace(target, previous)
        try:
            os.replace(replacement, target)
        except Exception:
            os.replace(previous, target)
            raise
        shutil.rmtree(previous, ignore_errors=True)
    _relocate_media_paths(target)
    prepare_data_dir(target)
    return target


def _relocate_media_paths(data_dir: Path) -> None:
    database = data_dir / "jobs.sqlite3"
    if not database.exists():
        return
    with closing(sqlite3.connect(database)) as connection:
        rows = connection.execute("SELECT job_id, payload_json FROM jobs").fetchall()
        for job_id, payload_json in rows:
            payload = json.loads(payload_json)
            suffix = Path(str(payload["filename"])).suffix.casefold()
            media_path = data_dir / "media" / str(job_id) / f"input{suffix}"
            connection.execute(
                "UPDATE jobs SET media_path = ? WHERE job_id = ?",
                (str(media_path), job_id),
            )
        connection.commit()
