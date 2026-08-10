from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from pydantic import ValidationError

from video_intelligence.errors import ErrorCode, StructuredError, VideoIntelligenceError
from video_intelligence.media.models import (
    MediaProbeResult,
    MediaStream,
    MediaValidationConfig,
    StreamType,
)


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: str
    stderr: str


class CommandRunner(Protocol):
    def run(
        self,
        arguments: Sequence[str],
        *,
        timeout_seconds: float,
        cancellation_requested: Callable[[], bool] | None = None,
    ) -> CommandResult: ...


class MediaProbeCancelled(Exception):
    """Raised after an active local media probe has been terminated."""


class SubprocessRunner:
    def run(
        self,
        arguments: Sequence[str],
        *,
        timeout_seconds: float,
        cancellation_requested: Callable[[], bool] | None = None,
    ) -> CommandResult:
        if cancellation_requested is not None:
            return self._run_cancellable(
                arguments,
                timeout_seconds=timeout_seconds,
                cancellation_requested=cancellation_requested,
            )
        try:
            completed = subprocess.run(
                list(arguments),
                check=False,
                capture_output=True,
                shell=False,
                text=True,
                timeout=timeout_seconds,
            )
        except FileNotFoundError as exc:
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.FFMPEG_UNAVAILABLE,
                    message="ffprobe is not installed or is not available on PATH.",
                    safe_recovery_action="Install FFmpeg locally and ensure ffprobe is on PATH.",
                )
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.PROVIDER_TIMEOUT,
                    message="ffprobe did not finish within the configured timeout.",
                    retryable=True,
                    safe_recovery_action="Retry with a smaller local media file.",
                )
            ) from exc
        return CommandResult(completed.returncode, completed.stdout, completed.stderr)

    def _run_cancellable(
        self,
        arguments: Sequence[str],
        *,
        timeout_seconds: float,
        cancellation_requested: Callable[[], bool],
    ) -> CommandResult:
        try:
            process = subprocess.Popen(
                list(arguments),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
                text=True,
            )
        except FileNotFoundError as exc:
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.FFMPEG_UNAVAILABLE,
                    message="ffprobe is not installed or is not available on PATH.",
                    safe_recovery_action="Install FFmpeg locally and ensure ffprobe is on PATH.",
                )
            ) from exc
        deadline = time.monotonic() + timeout_seconds
        while True:
            if cancellation_requested():
                process.kill()
                process.communicate()
                raise MediaProbeCancelled
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                process.kill()
                process.communicate()
                raise VideoIntelligenceError(
                    StructuredError(
                        code=ErrorCode.PROVIDER_TIMEOUT,
                        message="ffprobe did not finish within the configured timeout.",
                        retryable=True,
                        safe_recovery_action="Retry with a smaller local media file.",
                    )
                )
            try:
                stdout, stderr = process.communicate(timeout=min(0.05, remaining))
            except subprocess.TimeoutExpired:
                continue
            return CommandResult(cast(int, process.returncode), stdout, stderr)


def _domain_error(code: ErrorCode, message: str, recovery: str) -> VideoIntelligenceError:
    return VideoIntelligenceError(
        StructuredError(code=code, message=message, safe_recovery_action=recovery)
    )


def _safe_path(path: Path, config: MediaValidationConfig, allowed_root: Path | None) -> Path:
    resolved = path.resolve(strict=False)
    if allowed_root is not None:
        root = allowed_root.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise _domain_error(
                ErrorCode.UNAVAILABLE_MEDIA,
                "The media path is outside the permitted input directory.",
                "Select a media file inside the configured input directory.",
            )
    if not resolved.exists() or not resolved.is_file():
        raise _domain_error(
            ErrorCode.UNAVAILABLE_MEDIA,
            "The selected media file does not exist or is not a regular file.",
            "Select an existing local media file.",
        )
    if resolved.suffix.casefold() not in config.allowed_extensions:
        raise _domain_error(
            ErrorCode.UNSUPPORTED_CODEC,
            f"The file extension {resolved.suffix or '<none>'} is not supported.",
            "Select a supported AVI, M4V, MKV, MOV, MP4, or WebM file.",
        )
    if resolved.stat().st_size > config.max_file_size_bytes:
        raise _domain_error(
            ErrorCode.UNAVAILABLE_MEDIA,
            "The selected media file exceeds the configured size limit.",
            "Select a smaller file or explicitly increase the local size limit.",
        )
    return resolved


def _milliseconds(value: object) -> int | None:
    if value in (None, "", "N/A"):
        return None
    try:
        seconds = float(str(value))
    except ValueError:
        return None
    if seconds < 0:
        return None
    return round(seconds * 1000)


def _positive_int(value: object) -> int | None:
    try:
        parsed = int(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None


def _frame_rate(value: object) -> float | None:
    if value in (None, "", "0/0", "N/A"):
        return None
    text = str(value)
    try:
        if "/" in text:
            numerator, denominator = text.split("/", maxsplit=1)
            rate = float(numerator) / float(denominator)
        else:
            rate = float(text)
    except (ValueError, ZeroDivisionError):
        return None
    return rate if rate > 0 else None


def _stream(raw: dict[str, Any]) -> MediaStream:
    raw_type = raw.get("codec_type")
    known_types = {"video", "audio", "subtitle", "data", "attachment"}
    stream_type = cast(StreamType, str(raw_type) if raw_type in known_types else "unknown")
    return MediaStream(
        index=max(0, int(raw.get("index", 0))),
        stream_type=stream_type,
        codec_name=str(raw["codec_name"]) if raw.get("codec_name") else None,
        duration_ms=_milliseconds(raw.get("duration")),
        width=_positive_int(raw.get("width")),
        height=_positive_int(raw.get("height")),
        frame_rate=_frame_rate(raw.get("avg_frame_rate")),
        sample_rate_hz=_positive_int(raw.get("sample_rate")),
        channels=_positive_int(raw.get("channels")),
    )


def _validation_errors(
    streams: list[MediaStream], duration_ms: int | None, config: MediaValidationConfig
) -> tuple[list[str], list[StructuredError]]:
    warnings: list[str] = []
    errors: list[StructuredError] = []
    video_streams = [stream for stream in streams if stream.stream_type == "video"]
    audio_streams = [stream for stream in streams if stream.stream_type == "audio"]
    if not video_streams:
        errors.append(
            StructuredError(
                code=ErrorCode.MISSING_VIDEO,
                message="No video stream was detected.",
                safe_recovery_action="Select media containing a supported video stream.",
            )
        )
    if not audio_streams:
        detail = "No audio stream was detected."
        if config.require_audio:
            errors.append(
                StructuredError(
                    code=ErrorCode.MISSING_AUDIO,
                    message=detail,
                    safe_recovery_action=(
                        "Select media with audio or disable the audio requirement."
                    ),
                )
            )
        else:
            warnings.append(detail)
    for stream in video_streams:
        if stream.codec_name not in config.allowed_video_codecs:
            errors.append(
                StructuredError(
                    code=ErrorCode.UNSUPPORTED_CODEC,
                    message=f"Unsupported video codec: {stream.codec_name or 'unknown'}.",
                    safe_recovery_action="Transcode the file locally to H.264, HEVC, VP9, or AV1.",
                )
            )
    for stream in audio_streams:
        if stream.codec_name not in config.allowed_audio_codecs:
            errors.append(
                StructuredError(
                    code=ErrorCode.UNSUPPORTED_CODEC,
                    message=f"Unsupported audio codec: {stream.codec_name or 'unknown'}.",
                    safe_recovery_action="Transcode the audio locally to AAC, Opus, FLAC, or MP3.",
                )
            )
    if duration_ms is None:
        warnings.append("Reliable media duration was unavailable; no timestamp was fabricated.")
    elif duration_ms > config.max_duration_ms:
        errors.append(
            StructuredError(
                code=ErrorCode.UNAVAILABLE_MEDIA,
                message="The media duration exceeds the configured processing limit.",
                safe_recovery_action=(
                    "Select a shorter file or explicitly increase the local limit."
                ),
            )
        )
    return warnings, errors


class FFprobeClient:
    def __init__(
        self,
        *,
        binary: str = "ffprobe",
        runner: CommandRunner | None = None,
        require_discoverable_binary: bool = True,
    ) -> None:
        self.binary = binary
        self.runner = runner or SubprocessRunner()
        self.require_discoverable_binary = require_discoverable_binary

    def probe(
        self,
        path: Path,
        *,
        config: MediaValidationConfig | None = None,
        allowed_root: Path | None = None,
        cancellation_requested: Callable[[], bool] | None = None,
    ) -> MediaProbeResult:
        config = config or MediaValidationConfig()
        safe_path = _safe_path(path, config, allowed_root)
        if self.require_discoverable_binary and shutil.which(self.binary) is None:
            raise _domain_error(
                ErrorCode.FFMPEG_UNAVAILABLE,
                "ffprobe is not installed or is not available on PATH.",
                "Install FFmpeg locally and ensure ffprobe is on PATH.",
            )
        arguments = [
            self.binary,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-of",
            "json",
            str(safe_path),
        ]
        if cancellation_requested is None:
            completed = self.runner.run(
                arguments,
                timeout_seconds=config.subprocess_timeout_seconds,
            )
        else:
            completed = self.runner.run(
                arguments,
                timeout_seconds=config.subprocess_timeout_seconds,
                cancellation_requested=cancellation_requested,
            )
        if completed.returncode != 0:
            raise _domain_error(
                ErrorCode.UNAVAILABLE_MEDIA,
                "ffprobe could not read the selected media file.",
                "Verify the file is not corrupt and uses a supported container.",
            )
        try:
            payload: dict[str, Any] = json.loads(completed.stdout)
            raw_streams = payload.get("streams", [])
            if not isinstance(raw_streams, list):
                raise TypeError("streams must be a list")
            streams = [_stream(item) for item in raw_streams if isinstance(item, dict)]
            raw_format = payload.get("format", {})
            if not isinstance(raw_format, dict):
                raise TypeError("format must be an object")
            duration_ms = _milliseconds(raw_format.get("duration"))
            format_names = [
                name.strip()
                for name in str(raw_format.get("format_name", "")).split(",")
                if name.strip()
            ]
        except (json.JSONDecodeError, TypeError, ValueError, ValidationError) as exc:
            raise _domain_error(
                ErrorCode.SCHEMA_VALIDATION_FAILURE,
                "ffprobe returned malformed or unsupported metadata.",
                "Verify the file with a local FFmpeg installation.",
            ) from exc
        warnings, errors = _validation_errors(streams, duration_ms, config)
        return MediaProbeResult(
            path=str(safe_path),
            file_size_bytes=safe_path.stat().st_size,
            format_names=format_names,
            duration_ms=duration_ms,
            streams=streams,
            warnings=warnings,
            errors=errors,
        )


def probe_media(
    path: Path,
    *,
    config: MediaValidationConfig | None = None,
    allowed_root: Path | None = None,
    cancellation_requested: Callable[[], bool] | None = None,
) -> MediaProbeResult:
    return FFprobeClient().probe(
        path,
        config=config,
        allowed_root=allowed_root,
        cancellation_requested=cancellation_requested,
    )
