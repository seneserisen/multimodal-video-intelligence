from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Literal

from video_intelligence.command_center.controller import command_center_status
from video_intelligence.command_center.data import default_data_dir, prepare_data_dir
from video_intelligence.command_center.models import DoctorCheck, DoctorReport
from video_intelligence.command_center.store import JobStore
from video_intelligence.transcription.config import transcription_runtime_from_environment
from video_intelligence.transcription.providers import SUPPORTED_COMPUTE_TYPES, SUPPORTED_DEVICES


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
        database = storage / "jobs.sqlite3"
        if database.is_file():
            try:
                JobStore(database).load()
                database_status: Literal["ok", "warning", "error"] = "ok"
                database_detail = "Durable job database is readable."
                database_recovery = None
            except Exception:
                database_status = "error"
                database_detail = "Durable job database is unreadable."
                database_recovery = "Restore a verified backup or inspect the local database."
        else:
            database_status = "warning"
            database_detail = "Durable job database has not been created yet."
            database_recovery = "Start the command center to initialize durable jobs."
        checks.append(
            DoctorCheck(
                name="database",
                status=database_status,
                detail=database_detail,
                recovery_action=database_recovery,
            )
        )
        backup_dir = storage.with_name(f"{storage.name}Backups")
        backup_count = len(list(backup_dir.glob("mvi-backup-*.zip"))) if backup_dir.is_dir() else 0
        checks.append(
            DoctorCheck(
                name="backup",
                status="ok" if backup_count else "warning",
                detail=(
                    f"{backup_count} local backup archive(s) found."
                    if backup_count
                    else "No local backup archive found."
                ),
                recovery_action=None
                if backup_count
                else "Run BACKUP.bat while the app is stopped.",
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
    checks.extend(
        [
            DoctorCheck(
                name="faster_whisper_package",
                status="ok" if transcription.package_installed else "warning",
                detail=(
                    "Optional Faster-Whisper package is installed."
                    if transcription.package_installed
                    else "Optional Faster-Whisper package is not installed."
                ),
                recovery_action=(
                    None
                    if transcription.package_installed
                    else 'Install this project with the "transcription" extra.'
                ),
            ),
            DoctorCheck(
                name="model_path",
                status="ok" if transcription.model_configured else "warning",
                detail=(
                    "An explicit local model path is configured."
                    if transcription.model_configured
                    else "No explicit local model path is configured."
                ),
                recovery_action=(
                    None
                    if transcription.model_configured
                    else "Set VIDEO_INTELLIGENCE_WHISPER_MODEL to a local directory."
                ),
            ),
            DoctorCheck(
                name="model_ready",
                status="ok" if transcription.model_ready else "warning",
                detail=(
                    "Required local model files are present and parseable."
                    if transcription.model_ready
                    else transcription.status
                ),
                recovery_action=(
                    None
                    if transcription.model_ready
                    else "Configure a complete local CTranslate2 Whisper model."
                ),
            ),
            DoctorCheck(
                name="transcription_device",
                status="ok" if transcription.device in SUPPORTED_DEVICES else "error",
                detail=f"Configured device: {transcription.device}.",
                recovery_action=(
                    None if transcription.device in SUPPORTED_DEVICES else "Use auto, cpu, or cuda."
                ),
            ),
            DoctorCheck(
                name="transcription_compute_type",
                status=("ok" if transcription.compute_type in SUPPORTED_COMPUTE_TYPES else "error"),
                detail=f"Configured compute type: {transcription.compute_type}.",
                recovery_action=(
                    None
                    if transcription.compute_type in SUPPORTED_COMPUTE_TYPES
                    else "Choose a CTranslate2-supported compute type."
                ),
            ),
            DoctorCheck(
                name="model_loadable",
                status="warning",
                detail="Doctor does not load the model or perform inference.",
                recovery_action="Run a bounded authorized-media acceptance test.",
            ),
            DoctorCheck(
                name="real_inference",
                status="warning",
                detail="Real inference is not verified by Doctor.",
                recovery_action="Run a bounded authorized-media acceptance test.",
            ),
        ]
    )
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
