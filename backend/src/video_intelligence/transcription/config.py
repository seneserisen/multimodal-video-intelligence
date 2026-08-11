from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

from video_intelligence.transcription.providers import (
    SUPPORTED_COMPUTE_TYPES,
    SUPPORTED_DEVICES,
    FasterWhisperProvider,
    TranscriptionProvider,
    validate_local_model_directory,
)


@dataclass(frozen=True)
class TranscriptionRuntime:
    provider: TranscriptionProvider | None
    provider_name: str
    model_path: str | None
    status: str
    package_installed: bool
    model_configured: bool
    model_ready: bool
    device: str
    compute_type: str


def transcription_runtime_from_environment() -> TranscriptionRuntime:
    configured = os.environ.get("VIDEO_INTELLIGENCE_WHISPER_MODEL")
    package_installed = importlib.util.find_spec("faster_whisper") is not None
    device = os.environ.get("VIDEO_INTELLIGENCE_WHISPER_DEVICE", "cpu").casefold()
    compute_type = os.environ.get("VIDEO_INTELLIGENCE_WHISPER_COMPUTE_TYPE", "int8").casefold()
    if not configured:
        return TranscriptionRuntime(
            provider=None,
            provider_name="local-faster-whisper",
            model_path=None,
            status="Not configured; validation-only jobs remain available.",
            model_configured=False,
            model_ready=False,
            package_installed=package_installed,
            device=device,
            compute_type=compute_type,
        )
    model_path = Path(configured).expanduser().resolve(strict=False)
    model_error = validate_local_model_directory(model_path)
    if model_error is not None:
        return TranscriptionRuntime(
            provider=None,
            provider_name="local-faster-whisper",
            model_path=str(model_path),
            status=model_error,
            model_configured=True,
            model_ready=False,
            package_installed=package_installed,
            device=device,
            compute_type=compute_type,
        )
    if device not in SUPPORTED_DEVICES or compute_type not in SUPPORTED_COMPUTE_TYPES:
        return TranscriptionRuntime(
            provider=None,
            provider_name="local-faster-whisper",
            model_path=str(model_path),
            status="Configured device or compute type is unsupported.",
            model_configured=True,
            model_ready=True,
            package_installed=package_installed,
            device=device,
            compute_type=compute_type,
        )
    if not package_installed:
        return TranscriptionRuntime(
            provider=None,
            provider_name="local-faster-whisper",
            model_path=str(model_path),
            status="Local model found, but the optional Faster-Whisper package is not installed.",
            model_configured=True,
            model_ready=True,
            package_installed=package_installed,
            device=device,
            compute_type=compute_type,
        )
    provider = FasterWhisperProvider(
        model_path,
        device=device,
        compute_type=compute_type,
    )
    return TranscriptionRuntime(
        provider=provider,
        provider_name=provider.name,
        model_path=str(model_path),
        status=f"Ready on {device} with {compute_type} compute.",
        model_configured=True,
        model_ready=True,
        package_installed=package_installed,
        device=device,
        compute_type=compute_type,
    )
