from __future__ import annotations

import json
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

import pytest
from video_intelligence.errors import ErrorCode, VideoIntelligenceError
from video_intelligence.media.models import MediaValidationConfig
from video_intelligence.media.probe import (
    CommandResult,
    FFprobeClient,
    MediaProbeCancelled,
    SubprocessRunner,
)


class FakeRunner:
    def __init__(self, payload: dict[str, object] | str, returncode: int = 0) -> None:
        self.stdout = payload if isinstance(payload, str) else json.dumps(payload)
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
        assert timeout_seconds > 0
        assert cancellation_requested is None
        return CommandResult(self.returncode, self.stdout, "simulated stderr")


def fixture_payload(name: str = "ffprobe_valid.json") -> dict[str, object]:
    path = Path(__file__).parents[1] / "fixtures" / name
    value: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
    return value


def media_file(tmp_path: Path, suffix: str = ".mp4") -> Path:
    path = tmp_path / f"sample{suffix}"
    path.write_bytes(b"synthetic-media-placeholder")
    return path


def client(runner: FakeRunner) -> FFprobeClient:
    return FFprobeClient(runner=runner, require_discoverable_binary=False)


def test_valid_probe_uses_argument_array_and_parses_streams(tmp_path: Path) -> None:
    path = media_file(tmp_path)
    runner = FakeRunner(fixture_payload())
    report = client(runner).probe(path)

    assert report.valid
    assert report.has_video and report.has_audio
    assert report.duration_ms == 12_345
    assert report.streams[0].frame_rate == pytest.approx(29.97, rel=0.001)
    assert runner.arguments[-1] == str(path.resolve())
    assert runner.arguments[:3] == ["ffprobe", "-v", "error"]


def test_missing_audio_is_warning_or_error_by_configuration(tmp_path: Path) -> None:
    payload = fixture_payload()
    payload["streams"] = [payload["streams"][0]]  # type: ignore[index]
    warning_report = client(FakeRunner(payload)).probe(media_file(tmp_path))
    required_report = client(FakeRunner(payload)).probe(
        media_file(tmp_path), config=MediaValidationConfig(require_audio=True)
    )

    assert warning_report.valid
    assert warning_report.warnings == ["No audio stream was detected."]
    assert required_report.errors[0].code == ErrorCode.MISSING_AUDIO


def test_missing_video_and_unsupported_codec_are_structured(tmp_path: Path) -> None:
    payload = fixture_payload()
    audio = payload["streams"][1]  # type: ignore[index]
    payload["streams"] = [audio]
    missing_video = client(FakeRunner(payload)).probe(media_file(tmp_path))
    assert missing_video.errors[0].code == ErrorCode.MISSING_VIDEO

    payload = fixture_payload()
    payload["streams"][0]["codec_name"] = "mystery"  # type: ignore[index]
    unsupported = client(FakeRunner(payload)).probe(media_file(tmp_path))
    assert unsupported.errors[0].code == ErrorCode.UNSUPPORTED_CODEC


def test_missing_duration_is_preserved_as_unknown(tmp_path: Path) -> None:
    payload = fixture_payload()
    payload["format"] = {"format_name": "mp4"}
    report = client(FakeRunner(payload)).probe(media_file(tmp_path))
    assert report.duration_ms is None
    assert "no timestamp was fabricated" in report.warnings[-1]


@pytest.mark.parametrize("suffix", [".exe", ".txt", ""])
def test_unsupported_file_type_is_rejected(tmp_path: Path, suffix: str) -> None:
    with pytest.raises(VideoIntelligenceError) as caught:
        client(FakeRunner(fixture_payload())).probe(media_file(tmp_path, suffix))
    assert caught.value.detail.code == ErrorCode.UNSUPPORTED_CODEC


def test_path_outside_allowed_root_is_rejected(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = media_file(tmp_path)
    with pytest.raises(VideoIntelligenceError, match="outside"):
        client(FakeRunner(fixture_payload())).probe(outside, allowed_root=allowed)


def test_size_limit_and_malformed_output_are_structured(tmp_path: Path) -> None:
    path = media_file(tmp_path)
    with pytest.raises(VideoIntelligenceError) as too_large:
        client(FakeRunner(fixture_payload())).probe(
            path, config=MediaValidationConfig(max_file_size_bytes=1)
        )
    assert too_large.value.detail.code == ErrorCode.UNAVAILABLE_MEDIA

    with pytest.raises(VideoIntelligenceError) as malformed:
        client(FakeRunner("not json")).probe(path)
    assert malformed.value.detail.code == ErrorCode.SCHEMA_VALIDATION_FAILURE


def test_nonzero_ffprobe_exit_is_safe_and_structured(tmp_path: Path) -> None:
    with pytest.raises(VideoIntelligenceError) as caught:
        client(FakeRunner({}, returncode=1)).probe(media_file(tmp_path))
    assert caught.value.detail.code == ErrorCode.UNAVAILABLE_MEDIA
    assert "simulated stderr" not in caught.value.detail.message


def test_missing_ffprobe_is_structured(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("video_intelligence.media.probe.shutil.which", lambda _binary: None)
    with pytest.raises(VideoIntelligenceError) as caught:
        FFprobeClient().probe(media_file(tmp_path))
    assert caught.value.detail.code == ErrorCode.FFMPEG_UNAVAILABLE


def test_subprocess_runner_never_uses_a_shell(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}

    def fake_run(arguments: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured.update(kwargs)
        return subprocess.CompletedProcess(arguments, 0, stdout="{}", stderr="")

    monkeypatch.setattr("video_intelligence.media.probe.subprocess.run", fake_run)
    result = SubprocessRunner().run(["ffprobe", "input.mp4"], timeout_seconds=1)
    assert result.returncode == 0
    assert captured["shell"] is False


def test_subprocess_runner_terminates_an_active_cancelled_process() -> None:
    cancellation = threading.Event()
    timer = threading.Timer(0.1, cancellation.set)
    timer.start()
    started = time.monotonic()
    try:
        with pytest.raises(MediaProbeCancelled):
            SubprocessRunner().run(
                [sys.executable, "-c", "import time; time.sleep(10)"],
                timeout_seconds=5,
                cancellation_requested=cancellation.is_set,
            )
    finally:
        timer.cancel()
    assert time.monotonic() - started < 2
