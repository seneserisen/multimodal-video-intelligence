from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from video_intelligence.errors import ErrorCode, VideoIntelligenceError
from video_intelligence.media.probe import CommandResult
from video_intelligence.transcription import AudioExtractor


class FakeAudioRunner:
    def __init__(self, *, returncode: int = 0) -> None:
        self.returncode = returncode
        self.arguments: list[str] = []

    def run(
        self,
        arguments: Sequence[str],
        *,
        timeout_seconds: float,
        cancellation_requested: Callable[[], bool] | None = None,
    ) -> CommandResult:
        self.arguments = list(arguments)
        if self.returncode == 0:
            Path(arguments[-1]).write_bytes(b"RIFF-deterministic-wave")
        return CommandResult(self.returncode, "", "decode failed")


def test_audio_extraction_uses_safe_bounded_ffmpeg_arguments(tmp_path: Path) -> None:
    source = tmp_path / "path with spaces.mp4"
    source.write_bytes(b"synthetic-media")
    destination = tmp_path / "work" / "audio.wav"
    runner = FakeAudioRunner()

    result = AudioExtractor(runner=runner, timeout_seconds=15).extract(
        source,
        destination,
        lambda: False,
    )

    assert result == destination.resolve()
    assert runner.arguments[0] == "ffmpeg"
    assert "-nostdin" in runner.arguments
    assert runner.arguments[runner.arguments.index("-ac") + 1] == "1"
    assert runner.arguments[runner.arguments.index("-ar") + 1] == "16000"
    assert str(source.resolve()) in runner.arguments


def test_audio_extraction_failure_is_structured_and_removes_partial_output(
    tmp_path: Path,
) -> None:
    source = tmp_path / "corrupt.mp4"
    source.write_bytes(b"corrupt")
    destination = tmp_path / "audio.wav"

    with pytest.raises(VideoIntelligenceError) as caught:
        AudioExtractor(runner=FakeAudioRunner(returncode=1)).extract(
            source,
            destination,
            lambda: False,
        )

    assert caught.value.detail.code == ErrorCode.TRANSCRIPTION_FAILURE
    assert not destination.exists()
