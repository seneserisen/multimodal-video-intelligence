from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from video_intelligence.errors import ErrorCode, StructuredError, VideoIntelligenceError
from video_intelligence.media.probe import CommandRunner, SubprocessRunner


class AudioExtractor:
    def __init__(
        self,
        *,
        runner: CommandRunner | None = None,
        timeout_seconds: float = 3_600,
    ) -> None:
        self.runner = runner or SubprocessRunner()
        self.timeout_seconds = timeout_seconds

    def extract(
        self,
        media_path: Path,
        output_path: Path,
        cancellation_requested: Callable[[], bool],
    ) -> Path:
        source = media_path.resolve(strict=True)
        destination = output_path.resolve(strict=False)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        result = self.runner.run(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(source),
                "-vn",
                "-ac",
                "1",
                "-ar",
                "16000",
                "-c:a",
                "pcm_s16le",
                "-y",
                str(destination),
            ],
            timeout_seconds=self.timeout_seconds,
            cancellation_requested=cancellation_requested,
        )
        if result.returncode != 0 or not destination.is_file() or destination.stat().st_size == 0:
            destination.unlink(missing_ok=True)
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.TRANSCRIPTION_FAILURE,
                    message="FFmpeg could not extract usable audio from the selected media.",
                    safe_recovery_action="Verify that the media contains a supported audio stream.",
                )
            )
        return destination
