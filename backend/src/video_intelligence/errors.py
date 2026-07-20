from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ErrorCode(StrEnum):
    INVALID_URL = "invalid_url"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    UNAVAILABLE_MEDIA = "unavailable_media"
    DIRECT_PROVIDER_FAILURE = "direct_provider_failure"
    EXTRACTOR_FAILURE = "extractor_failure"
    TAB_CAPTURE_FAILURE = "tab_capture_failure"
    MISSING_AUDIO = "missing_audio"
    MISSING_VIDEO = "missing_video"
    SILENT_CAPTURE = "silent_capture"
    BLACK_CAPTURE = "black_capture"
    FROZEN_VIDEO = "frozen_video"
    INCOMPLETE_RECORDING = "incomplete_recording"
    UNSUPPORTED_CODEC = "unsupported_codec"
    FFMPEG_UNAVAILABLE = "ffmpeg_unavailable"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MISSING_API_KEY = "missing_api_key"
    PROVIDER_QUOTA = "provider_quota_or_rate_limit"
    PROVIDER_TIMEOUT = "provider_timeout"
    MALFORMED_PROVIDER_OUTPUT = "malformed_provider_output"
    SCHEMA_VALIDATION_FAILURE = "schema_validation_failure"
    TRANSCRIPTION_FAILURE = "transcription_failure"
    OCR_FAILURE = "ocr_failure"
    VISUAL_ANALYSIS_FAILURE = "visual_analysis_failure"
    CLEANUP_FAILURE = "cleanup_failure"


class StructuredError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = "1.0.0"
    code: ErrorCode
    message: str
    retryable: bool = False
    safe_recovery_action: str | None = None
    internal_context: dict[str, Any] = Field(default_factory=dict, exclude=True)


class VideoIntelligenceError(Exception):
    def __init__(self, detail: StructuredError) -> None:
        super().__init__(detail.message)
        self.detail = detail
