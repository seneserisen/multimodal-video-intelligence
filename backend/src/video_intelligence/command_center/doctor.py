from __future__ import annotations

import shutil
import sys
from pathlib import Path

from video_intelligence.command_center.controller import command_center_status
from video_intelligence.command_center.data import default_data_dir, prepare_data_dir
from video_intelligence.command_center.models import DoctorCheck, DoctorReport
from video_intelligence.transcription.config import transcription_runtime_from_environment


def run_doctor(
    state_dir: Path | None = None,
    data_dir: Path | None = None,
) -> DoctorReport:
    checks: list[DoctorCheck] = []
    version = sys.version_info
    python_ok = version >= (3, 12)
    checks.append(
        DoctorCheck(
            name="python",
            status="ok" if python_ok else "error",
            detail=f"Python {version.major}.{version.minor}.{version.micro}",
            recovery_action=None if python_ok else "Install Python 3.12 or newer.",
        )
    )
    for binary in ("ffmpeg", "ffprobe"):
        location = shutil.which(binary)
        checks.append(
            DoctorCheck(
                name=binary,
                status="ok" if location else "warning",
                detail=location or f"{binary} is not available on PATH.",
                recovery_action=(
                    None if location else "Install FFmpeg and restart the terminal or application."
                ),
            )
        )
    try:
        storage = prepare_data_dir(
            data_dir or (state_dir / "data" if state_dir else default_data_dir())
        )
        free_bytes = shutil.disk_usage(storage).free
        enough_space = free_bytes >= 1024**3
        checks.append(
            DoctorCheck(
                name="data_storage",
                status="ok" if enough_space else "warning",
                detail=f"{storage} ({free_bytes // 1024**2} MiB free)",
                recovery_action=(
                    None
                    if enough_space
                    else "Free at least 1 GiB before processing additional video."
                ),
            )
        )
    except OSError:
        checks.append(
            DoctorCheck(
                name="data_storage",
                status="error",
                detail="The local data directory is unavailable.",
                recovery_action="Choose a writable local data directory.",
            )
        )
    transcription = transcription_runtime_from_environment()
    checks.append(
        DoctorCheck(
            name="transcription",
            status="ok" if transcription.provider is not None else "warning",
            detail=transcription.status,
            recovery_action=(
                None
                if transcription.provider is not None
                else "Configure an optional local model to enable real transcription."
            ),
        )
    )
    service = command_center_status(state_dir)
    checks.append(
        DoctorCheck(
            name="command_center",
            status="ok" if service.running else "warning",
            detail=service.message,
            recovery_action=None if service.running else "Run video-intelligence start.",
        )
    )
    return DoctorReport(
        ready=not any(check.status == "error" for check in checks),
        checks=checks,
    )
