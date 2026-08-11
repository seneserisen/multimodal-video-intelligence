from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

import pytest
from video_intelligence.errors import ErrorCode, VideoIntelligenceError
from video_intelligence.media.probe import CommandResult
from video_intelligence.transcription import AudioExtractor
from video_intelligence.transcription.config import transcription_runtime_from_environment


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


def test_runtime_rejects_model_name_and_incomplete_local_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIDEO_INTELLIGENCE_WHISPER_MODEL", "tiny")
    runtime = transcription_runtime_from_environment()
    assert runtime.provider is None
    assert runtime.model_ready is False
    assert "does not exist" in runtime.status

    empty = tmp_path / "model with spaces"
    empty.mkdir()
    monkeypatch.setenv("VIDEO_INTELLIGENCE_WHISPER_MODEL", str(empty))
    runtime = transcription_runtime_from_environment()
    assert runtime.provider is None
    assert runtime.model_configured is True
    assert "model.bin" in runtime.status


def test_runtime_rejects_unsupported_device_without_silent_cpu_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = tmp_path / "model"
    model.mkdir()
    (model / "model.bin").write_bytes(b"model")
    (model / "config.json").write_text("{}", encoding="utf-8")
    (model / "tokenizer.json").write_text("{}", encoding="utf-8")
    monkeypatch.setenv("VIDEO_INTELLIGENCE_WHISPER_MODEL", str(model))
    monkeypatch.setenv("VIDEO_INTELLIGENCE_WHISPER_DEVICE", "quantum")

    runtime = transcription_runtime_from_environment()

    assert runtime.provider is None
    assert runtime.device == "quantum"
    assert "unsupported" in runtime.status
