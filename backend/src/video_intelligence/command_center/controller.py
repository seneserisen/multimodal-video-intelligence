from __future__ import annotations

import json
import os
import secrets
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

from video_intelligence import __version__
from video_intelligence.command_center.models import (
    CommandCenterStatus,
    RuntimeState,
    StartResult,
)
from video_intelligence.command_center.state import (
    default_state_dir,
    log_path,
    prepare_state_dir,
    read_state,
    remove_state,
)
from video_intelligence.errors import ErrorCode, StructuredError, VideoIntelligenceError


def _error(code: ErrorCode, message: str, recovery: str) -> VideoIntelligenceError:
    return VideoIntelligenceError(
        StructuredError(code=code, message=message, safe_recovery_action=recovery)
    )


def _request(
    state: RuntimeState, path: str, *, method: str = "GET", timeout: float = 1.0
) -> dict[str, object]:
    request = urllib.request.Request(
        f"http://127.0.0.1:{state.port}{path}",
        method=method,
        headers={"Authorization": f"Bearer {state.token}"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        payload: dict[str, object] = json.loads(response.read().decode("utf-8"))
        return payload


def _healthy_status(state: RuntimeState) -> CommandCenterStatus | None:
    try:
        payload = _request(state, "/api/status")
        return CommandCenterStatus.model_validate(payload)
    except (OSError, ValueError, urllib.error.URLError):
        return None


def _pid_exists(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def command_center_status(state_dir: Path | None = None) -> CommandCenterStatus:
    state = read_state(state_dir)
    if state is None:
        return CommandCenterStatus(
            running=False,
            version=__version__,
            message="Command center is stopped.",
        )
    healthy = _healthy_status(state)
    if healthy is not None:
        return healthy
    return CommandCenterStatus(
        running=False,
        pid=state.pid,
        port=state.port,
        started_at=state.started_at,
        version=state.version,
        message=(
            "Command center state exists but the authenticated health check failed."
            if _pid_exists(state.pid)
            else "Command center stopped unexpectedly; stale state can be replaced on start."
        ),
    )


def _launch_service(state_dir: Path, port: int, token: str, max_upload_bytes: int) -> None:
    environment = os.environ.copy()
    environment["VIDEO_INTELLIGENCE_CC_TOKEN"] = token
    arguments = [
        sys.executable,
        "-m",
        "video_intelligence.command_center.server",
        "--state-dir",
        str(state_dir),
        "--port",
        str(port),
        "--max-upload-bytes",
        str(max_upload_bytes),
    ]
    flags = 0
    if os.name == "nt":
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
    with log_path(state_dir).open("ab") as service_log:
        subprocess.Popen(
            arguments,
            cwd=Path(__file__).resolve().parents[4],
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=service_log,
            stderr=service_log,
            shell=False,
            close_fds=True,
            creationflags=flags,
            start_new_session=os.name != "nt",
        )


def command_center_start(
    *,
    state_dir: Path | None = None,
    port: int = 0,
    open_browser: bool = True,
    startup_timeout_seconds: float = 8.0,
    max_upload_bytes: int = 512 * 1024**2,
) -> StartResult:
    directory = prepare_state_dir(state_dir or default_state_dir())
    existing = read_state(directory)
    if existing is not None:
        healthy = _healthy_status(existing)
        if healthy is not None:
            url = f"http://127.0.0.1:{existing.port}/#token={urllib.parse.quote(existing.token)}"
            if open_browser:
                webbrowser.open(url, new=2)
            return StartResult(status=healthy, dashboard_url=url, already_running=True)
        if _pid_exists(existing.pid):
            raise _error(
                ErrorCode.COMMAND_CENTER_ALREADY_RUNNING,
                "A command-center process exists but did not pass its health check.",
                "Run stop or inspect the command-center log before retrying.",
            )
        remove_state(directory, expected_pid=existing.pid)

    token = secrets.token_urlsafe(32)
    try:
        _launch_service(directory, port, token, max_upload_bytes)
    except OSError as exc:
        raise _error(
            ErrorCode.COMMAND_CENTER_UNAVAILABLE,
            "The local command-center process could not be launched.",
            f"Inspect the local service log at {log_path(directory)}.",
        ) from exc
    deadline = time.monotonic() + startup_timeout_seconds
    state: RuntimeState | None = None
    status: CommandCenterStatus | None = None
    while time.monotonic() < deadline:
        state = read_state(directory)
        if state is not None:
            status = _healthy_status(state)
            if status is not None:
                break
        time.sleep(0.1)
    if state is None or status is None:
        raise _error(
            ErrorCode.COMMAND_CENTER_UNAVAILABLE,
            "The local command center did not become healthy in time.",
            f"Inspect the local service log at {log_path(directory)}.",
        )
    url = f"http://127.0.0.1:{state.port}/#token={urllib.parse.quote(state.token)}"
    if open_browser:
        webbrowser.open(url, new=2)
    return StartResult(status=status, dashboard_url=url)


def command_center_stop(
    *, state_dir: Path | None = None, shutdown_timeout_seconds: float = 5.0
) -> CommandCenterStatus:
    directory = state_dir or default_state_dir()
    state = read_state(directory)
    if state is None:
        return CommandCenterStatus(
            running=False,
            version=__version__,
            message="Command center is already stopped.",
        )
    try:
        _request(state, "/api/stop", method="POST")
    except (OSError, ValueError, urllib.error.URLError) as exc:
        if _pid_exists(state.pid):
            raise _error(
                ErrorCode.COMMAND_CENTER_UNAVAILABLE,
                "The command center did not accept the authenticated stop request.",
                "Inspect the service log; no process was forcefully terminated.",
            ) from exc
        remove_state(directory, expected_pid=state.pid)
    deadline = time.monotonic() + shutdown_timeout_seconds
    while time.monotonic() < deadline and read_state(directory) is not None:
        time.sleep(0.1)
    if read_state(directory) is not None:
        raise _error(
            ErrorCode.COMMAND_CENTER_UNAVAILABLE,
            "The command center did not stop within the configured timeout.",
            "Retry status and inspect the service log.",
        )
    return CommandCenterStatus(
        running=False,
        version=__version__,
        message="Command center stopped cleanly.",
    )
