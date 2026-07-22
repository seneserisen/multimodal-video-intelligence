from __future__ import annotations

import argparse
import json
import os
import secrets
import threading
from datetime import UTC, datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from video_intelligence import __version__
from video_intelligence.command_center.dashboard import (
    DASHBOARD_CSS,
    DASHBOARD_HTML,
    DASHBOARD_JS,
)
from video_intelligence.command_center.models import CommandCenterStatus, RuntimeState
from video_intelligence.command_center.state import remove_state, write_state


class CommandCenterHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, address: tuple[str, int], token: str, state_dir: Path) -> None:
        super().__init__(address, CommandCenterHandler)
        self.token = token
        self.state_dir = state_dir
        self.started_at = datetime.now(UTC)

    def public_status(self) -> CommandCenterStatus:
        return CommandCenterStatus(
            running=True,
            pid=os.getpid(),
            port=self.server_port,
            started_at=self.started_at,
            version=__version__,
            message="Local command center is healthy.",
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
            if not self._authorized():
                self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
                return
            self._json(
                HTTPStatus.OK,
                self.server.public_status().model_dump(mode="json"),
            )
            return
        self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})

    def do_POST(self) -> None:
        path = urlsplit(self.path).path
        if not self._authorized():
            self._json(HTTPStatus.UNAUTHORIZED, {"error": "unauthorized"})
            return
        if path != "/api/stop":
            self._json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
            return
        self._json(HTTPStatus.ACCEPTED, {"stopping": True})
        threading.Thread(target=self.server.shutdown, daemon=True).start()


def run_server(state_dir: Path, port: int) -> None:
    token = os.environ.get("VIDEO_INTELLIGENCE_CC_TOKEN")
    if token is None or len(token) < 32:
        raise RuntimeError("A command-center token is required.")
    server = CommandCenterHTTPServer(("127.0.0.1", port), token, state_dir)
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
        server.server_close()
        remove_state(state_dir, expected_pid=os.getpid())


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--state-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=0)
    args = parser.parse_args()
    run_server(args.state_dir, args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
