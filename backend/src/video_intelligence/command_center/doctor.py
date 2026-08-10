from __future__ import annotations

import shutil
import sys
from pathlib import Path

from video_intelligence.command_center.controller import command_center_status
from video_intelligence.command_center.models import DoctorCheck, DoctorReport


def run_doctor(state_dir: Path | None = None) -> DoctorReport:
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
