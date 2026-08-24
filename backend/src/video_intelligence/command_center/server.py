from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import threading
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit

from video_intelligence import __version__
from video_intelligence.command_center.dashboard import (
    DASHBOARD_CSS,
    DASHBOARD_HTML,
    DASHBOARD_JS,
)
from video_intelligence.command_center.data import prepare_data_dir
from video_intelligence.command_center.jobs import (
    DuplicateMediaError,
    JobCapacityError,
    JobManager,
    JobNotFoundError,
    JobStateError,
    MediaJobProcessor,
    ProcessingJobList,
)
from video_intelligence.command_center.models import CommandCenterStatus, RuntimeState
from video_intelligence.command_center.state import remove_state, write_state
from video_intelligence.command_center.store import JobStore
from video_intelligence.media import MediaValidationConfig
from video_intelligence.transcription.config import transcription_runtime_from_environment


class CommandCenterHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        address: tuple[str, int],
        token: str,
        state_dir: Path,
        max_upload_bytes: int,
        data_dir: Path | None = None,
    ) -> None:
        super().__init__(address, CommandCenterHandler)
        self.token = token
        self.state_dir = state_dir
        self.started_at = datetime.now(UTC)
        self.max_upload_bytes = max_upload_bytes
        self.media_config = MediaValidationConfig(max_file_size_bytes=max_upload_bytes)
        self.data_dir = prepare_data_dir(data_dir or state_dir / "data")
        self.transcription_runtime = transcription_runtime_from_environment()
        store = JobStore(self.data_dir / "jobs.sqlite3")
        processor = MediaJobProcessor(
            self.data_dir / "work",
            transcription_provider=self.transcription_runtime.provider,
        )
        self.job_manager = JobManager(
            self.data_dir / "media",
            processor=processor,
            store=store,
        )

    def public_status(self) -> CommandCenterStatus:
        active, completed, failed = self.job_manager.counts()
        return CommandCenterStatus(
            running=True,
            pid=os.getpid(),
            port=self.server_port,
            started_at=self.started_at,
            version=__version__,
            message="Local command center is healthy.",
            active_jobs=active,
            completed_jobs=completed,
            failed_jobs=failed,
            max_upload_bytes=self.max_upload_bytes,
            max_active_jobs=self.job_manager.max_active_jobs,
            data_dir=str(self.data_dir),
            transcription_available=self.transcription_runtime.provider is not None,
            transcription_provider=self.transcription_runtime.provider_name,
            transcription_model_path=self.transcription_runtime.model_path,
            transcription_status=self.transcription_runtime.status,
        )


class CommandCenterHandler(BaseHTTPRequestHandler):
    server: CommandCenterHTTPServer

    def log_message(self, format: str, *args: object) -> None:
        return

    def _headers(self, content_type: str, length: int) -> None:
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'",
        )

    def _send(self, status: HTTPStatus, body: bytes, content_type: str) -> None:
        self.send_response(status)
        self._headers(content_type, len(body))
        self.end_headers()
        self.wfile.write(body)

    def _json(self, status: HTTPStatus, payload: object) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8")

    def _authorized(self) -> bool:
        expected = f"Bearer {self.server.token}"
        supplied = self.headers.get("Authorization", "")
        return secrets.compare_digest(supplied, expected)

    def _api_allowed(self) -> bool:
        origin = self.headers.get("Origin")
        expected_origin = f"http://127.0.0.1:{self.server.server_port}"
        if origin is not None and origin != expected_origin:
            self._json(HTTPStatus.FORBIDDEN, {"error": "origin_not_allowed"})
            return False
        if not self._authorized():
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return False
        return True

    def _job_id_from_path(self, path: str, suffix: str = "") -> str | None:
        prefix = "/api/jobs/"
        if not path.startswith(prefix):
            return None
        remainder = path[len(prefix) :]
        if suffix:
            if not remainder.endswith(suffix):
                return None
            remainder = remainder[: -len(suffix)]
        if not remainder or "/" in remainder:
            return None
        return remainder

    def do_GET(self) -> None:
        path = urlsplit(self.path).path
        assets = {
            "/": (DASHBOARD_HTML.encode(), "text/html; charset=utf-8"),
            "/app.js": (DASHBOARD_JS.encode(), "text/javascript; charset=utf-8"),
            "/styles.css": (DASHBOARD_CSS.encode(), "text/css; charset=utf-8"),
        }
        if path in assets:
            body, content_type = assets[path]
            self._send(HTTPStatus.OK, body, content_type)
            return
        if path == "/api/status":
            if not self._api_allowed():
                return
            self._json(
                HTTPStatus.OK,
                self.server.public_status().model_dump(mode="json"),
            )
            return
        if path == "/api/jobs":
            if not self._api_allowed():
                return
            jobs = ProcessingJobList(jobs=self.server.job_manager.list())
            self._json(HTTPStatus.OK, jobs.model_dump(mode="json"))
            return
        job_id = self._job_id_from_path(path)
        if job_id is not None:
            if not self._api_allowed():
                return
            try:
                job = self.server.job_manager.get(job_id)
            except JobNotFoundError:
                self._json(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
                return
            self._json(HTTPStatus.OK, job.model_dump(mode="json"))
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if not self._api_allowed():
            return
        if path == "/api/stop":
            self._json(HTTPStatus.ACCEPTED, {"stopping": True})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if path == "/api/jobs":
            self._upload_job()
            return
        job_id = self._job_id_from_path(path, "/cancel")
        if job_id is not None:
            try:
                job = self.server.job_manager.cancel(job_id)
            except JobNotFoundError:
                self._json(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
                return
            self._json(HTTPStatus.OK, job.model_dump(mode="json"))
            return
        job_id = self._job_id_from_path(path, "/retry")
        if job_id is not None:
            try:
                job = self.server.job_manager.retry(job_id)
            except JobNotFoundError:
                self._json(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
                return
            except JobStateError:
                self._json(HTTPStatus.CONFLICT, {"error": "job_cannot_be_retried"})
                return
            self._json(HTTPStatus.ACCEPTED, job.model_dump(mode="json"))
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_PATCH(self) -> None:
        path = urlsplit(self.path).path
        if not self._api_allowed():
            return
        parts = path.split("/")
        if len(parts) != 6 or parts[1:3] != ["api", "jobs"] or parts[4] != "transcript":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        job_id, evidence_id = parts[3], parts[5]
        if not job_id or not evidence_id or len(job_id) > 64 or len(evidence_id) > 128:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_transcript_reference"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            content_length = -1
        if content_length <= 0 or content_length > 24_000:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid_edit_size"})
            return
        try:
            payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
            if not isinstance(payload, dict) or set(payload) != {"text"}:
                raise ValueError
            text = payload["text"]
            if not isinstance(text, str):
                raise ValueError
            job = self.server.job_manager.edit_transcript(job_id, evidence_id, text)
        except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_transcript_edit"})
            return
        except JobNotFoundError:
            self._json(HTTPStatus.NOT_FOUND, {"error": "transcript_item_not_found"})
            return
        except JobStateError:
            self._json(HTTPStatus.CONFLICT, {"error": "transcript_cannot_be_edited"})
            return
        self._json(HTTPStatus.OK, job.model_dump(mode="json"))

    def do_DELETE(self) -> None:
        path = urlsplit(self.path).path
        if not self._api_allowed():
            return
        job_id = self._job_id_from_path(path)
        if job_id is None:
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        try:
            self.server.job_manager.remove(job_id)
        except JobNotFoundError:
            self._json(HTTPStatus.NOT_FOUND, {"error": "job_not_found"})
            return
        except JobStateError:
            self._json(HTTPStatus.CONFLICT, {"error": "job_is_active"})
            return
        self._send(HTTPStatus.NO_CONTENT, b"", "application/json")

    def _upload_job(self) -> None:
        if self.headers.get("X-MVI-Authorized", "").casefold() != "true":
            self._json(HTTPStatus.FORBIDDEN, {"error": "authorization_confirmation_required"})
            return
        raw_filename = self.headers.get("X-Filename", "")
        try:
            filename = unquote(raw_filename, errors="strict")
        except UnicodeDecodeError:
            self._json(HTTPStatus.BAD_REQUEST, {"error": "invalid_filename"})
            return
        if (
            not filename
            or len(filename) > 255
            or Path(filename).name != filename
            or Path(filename).suffix.casefold() not in self.server.media_config.allowed_extensions
        ):
            self._json(HTTPStatus.BAD_REQUEST, {"error": "unsupported_filename"})
            return
        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            content_length = -1
        if content_length <= 0 or content_length > self.server.max_upload_bytes:
            self._json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "invalid_upload_size"})
            return
        transcribe = self.headers.get("X-MVI-Transcribe", "").casefold() == "true"
        if transcribe and self.server.transcription_runtime.provider is None:
            self._json(HTTPStatus.CONFLICT, {"error": "transcription_not_configured"})
            return
        job_id = secrets.token_hex(12)
        try:
            _job, upload_path = self.server.job_manager.reserve(
                job_id,
                filename,
                transcribe=transcribe,
            )
        except JobCapacityError:
            self._json(HTTPStatus.TOO_MANY_REQUESTS, {"error": "job_capacity_reached"})
            return
        remaining = content_length
        digest = hashlib.sha256()
        try:
            self.connection.settimeout(30)
            with upload_path.open("xb") as destination:
                while remaining:
                    chunk = self.rfile.read(min(1024 * 1024, remaining))
                    if not chunk:
                        raise OSError("upload ended before the declared content length")
                    destination.write(chunk)
                    digest.update(chunk)
                    remaining -= len(chunk)
            job = self.server.job_manager.submit(job_id, content_sha256=digest.hexdigest())
        except DuplicateMediaError as exc:
            self._json(
                HTTPStatus.CONFLICT,
                {"error": "duplicate_media", "existing_job_id": exc.existing_job_id},
            )
            return
        except OSError:
            job = self.server.job_manager.fail_upload(
                job_id,
                "The upload did not complete within the declared size and timeout limits.",
            )
            self._json(HTTPStatus.BAD_REQUEST, job.model_dump(mode="json"))
            return
        self._json(HTTPStatus.ACCEPTED, job.model_dump(mode="json"))


def run_server(state_dir: Path, data_dir: Path, port: int, max_upload_bytes: int) -> None:
    token = os.environ.get("VIDEO_INTELLIGENCE_CC_TOKEN")
    if token is None or len(token) < 32:
        raise RuntimeError("A command-center token is required.")
    server = CommandCenterHTTPServer(
        ("127.0.0.1", port),
        token,
        state_dir,
        max_upload_bytes,
        data_dir,
    )
    state = RuntimeState(
        pid=os.getpid(),
        port=server.server_port,
        token=token,
        started_at=server.started_at,
        version=__version__,
    )
    write_state(state, state_dir)
    try:
        server.serve_forever(poll_interval=0.2)
    finally:
        server.job_manager.shutdown()
        server.server_close()
        remove_state(state_dir, expected_pid=os.getpid())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--max-upload-bytes", type=int, required=True)
    args = parser.parse_args()
    run_server(args.state_dir, args.data_dir, args.port, args.max_upload_bytes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
