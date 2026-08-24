from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_intelligence.command_center.jobs import ProcessingJob


class JobStore:
    SCHEMA_VERSION = 1

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path.resolve(strict=False)
        self.database_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS schema_info (
                    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
                    version INTEGER NOT NULL
                )
                """
            )
            row = connection.execute(
                "SELECT version FROM schema_info WHERE singleton = 1"
            ).fetchone()
            if row is not None and int(row["version"]) > self.SCHEMA_VERSION:
                raise RuntimeError("The local job database was created by a newer application.")
            connection.execute(
                "INSERT OR REPLACE INTO schema_info(singleton, version) VALUES (1, ?)",
                (self.SCHEMA_VERSION,),
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL,
                    content_sha256 TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    media_path TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
                """
            )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at DESC)"
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_jobs_content_sha256
                ON jobs(content_sha256) WHERE content_sha256 IS NOT NULL
                """
            )
            connection.execute("PRAGMA optimize")

    def save(self, job: ProcessingJob, media_path: Path) -> None:
        payload = json.dumps(
            job.model_dump(mode="json", exclude_computed_fields=True),
            ensure_ascii=False,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO jobs(
                    job_id, status, content_sha256, created_at, updated_at, media_path, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_id) DO UPDATE SET
                    status = excluded.status,
                    content_sha256 = excluded.content_sha256,
                    updated_at = excluded.updated_at,
                    media_path = excluded.media_path,
                    payload_json = excluded.payload_json
                """,
                (
                    job.job_id,
                    str(job.status),
                    job.content_sha256,
                    job.created_at.isoformat(),
                    job.updated_at.isoformat(),
                    str(media_path.resolve(strict=False)),
                    payload,
                ),
            )

    def load(self) -> list[tuple[ProcessingJob, Path]]:
        from video_intelligence.command_center.jobs import ProcessingJob

        with self._connect() as connection:
            rows = connection.execute(
                "SELECT payload_json, media_path FROM jobs ORDER BY created_at DESC"
            ).fetchall()
        return [
            (ProcessingJob.model_validate_json(row["payload_json"]), Path(row["media_path"]))
            for row in rows
        ]

    def delete(self, job_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM jobs WHERE job_id = ?", (job_id,))

    def duplicate_job_id(self, content_sha256: str, *, exclude_job_id: str) -> str | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT job_id FROM jobs
                WHERE content_sha256 = ? AND job_id != ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (content_sha256, exclude_job_id),
            ).fetchone()
        return None if row is None else str(row["job_id"])

    def backup_to(self, destination: Path) -> Path:
        target = destination.resolve(strict=False)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with (
            closing(sqlite3.connect(self.database_path)) as source,
            closing(sqlite3.connect(target)) as backup,
        ):
            source.backup(backup)
        return target
