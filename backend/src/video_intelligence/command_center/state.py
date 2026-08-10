from __future__ import annotations

import getpass
import json
import os
import re
import tempfile
from contextlib import suppress
from pathlib import Path

from pydantic import ValidationError

from video_intelligence.command_center.models import RuntimeState


def default_state_dir() -> Path:
    username = re.sub(r"[^A-Za-z0-9_.-]", "_", getpass.getuser()) or "user"
    return Path(tempfile.gettempdir()) / f"mvi-command-center-{username}"


def state_path(state_dir: Path | None = None) -> Path:
    return (state_dir or default_state_dir()) / "state.json"


def log_path(state_dir: Path | None = None) -> Path:
    return (state_dir or default_state_dir()) / "service.log"


def prepare_state_dir(state_dir: Path | None = None) -> Path:
    directory = state_dir or default_state_dir()
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    with suppress(OSError):
        directory.chmod(0o700)
    return directory


def write_state(state: RuntimeState, state_dir: Path | None = None) -> Path:
    directory = prepare_state_dir(state_dir)
    target = state_path(directory)
    temporary = target.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(state.model_dump(mode="json"), indent=2) + "\n",
        encoding="utf-8",
    )
    with suppress(OSError):
        temporary.chmod(0o600)
    os.replace(temporary, target)
    return target


def read_state(state_dir: Path | None = None) -> RuntimeState | None:
    target = state_path(state_dir)
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
        return RuntimeState.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError):
        return None


def remove_state(state_dir: Path | None = None, *, expected_pid: int | None = None) -> bool:
    target = state_path(state_dir)
    current = read_state(state_dir)
    if expected_pid is not None and current is not None and current.pid != expected_pid:
        return False
    try:
        target.unlink(missing_ok=True)
    except OSError:
        return False
    return True
