from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

from video_intelligence.transcription.providers import (
    FasterWhisperProvider,
    TranscriptionProvider,
)


@dataclass(frozen=True)
class TranscriptionRuntime:
    provider: TranscriptionProvider | None
    provider_name: str
    model_path: str | None
    status: str


def transcription_runtime_from_environment() -> TranscriptionRuntime:
    configured = os.environ.get("VIDEO_INTELLIGENCE_WHISPER_MODEL")
    if not configured:
        return TranscriptionRuntime(
            provider=None,
            provider_name="local-faster-whisper",
            model_path=None,
            status="Not configured; validation-only jobs remain available.",
        )
    model_path = Path(configured).expanduser().resolve(strict=False)
    if not model_path.is_dir():
        return TranscriptionRuntime(
            provider=None,
            provider_name="local-faster-whisper",
            model_path=str(model_path),
            status="Configured model directory does not exist.",
        )
    if importlib.util.find_spec("faster_whisper") is None:
        return TranscriptionRuntime(
            provider=None,
            provider_name="local-faster-whisper",
            model_path=str(model_path),
            status="Local model found, but the optional Faster-Whisper package is not installed.",
        )
    device = os.environ.get("VIDEO_INTELLIGENCE_WHISPER_DEVICE", "cpu").casefold()
    if device not in {"cpu", "cuda", "auto"}:
        device = "cpu"
    compute_type = os.environ.get("VIDEO_INTELLIGENCE_WHISPER_COMPUTE_TYPE", "int8")
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
    )
