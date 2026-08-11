from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from video_intelligence.errors import ErrorCode, VideoIntelligenceError
from video_intelligence.models import EvidenceItem
from video_intelligence.providers.fake import DeterministicFakeEvidenceProvider, FailingFakeProvider
from video_intelligence.transcription import FasterWhisperProvider
from video_intelligence.transcription.providers import TranscriptionCancelled


def local_model(directory: Path) -> Path:
    directory.mkdir()
    (directory / "model.bin").write_bytes(b"local-model")
    (directory / "config.json").write_text('{"model_type":"whisper"}', encoding="utf-8")
    (directory / "tokenizer.json").write_text('{"version":"1.0"}', encoding="utf-8")
    return directory


def test_fake_provider_is_deterministic_and_returns_copies() -> None:
    item = EvidenceItem(
        evidence_id="one",
        modality="speech",
        evidence_type="transcript",
        text="hello",
        confidence=1,
        provider="fake",
        processing_version="1",
    )
    provider = DeterministicFakeEvidenceProvider("fake", [item])
    first = provider.transcribe(
        Path("unused"), source_reference="video.mp4", cancellation_requested=lambda: False
    )
    second = provider.transcribe(
        Path("unused"), source_reference="video.mp4", cancellation_requested=lambda: False
    )
    assert first == second
    assert first.evidence_items is not second.evidence_items


def test_provider_failure_is_structured() -> None:
    with pytest.raises(VideoIntelligenceError) as caught:
        FailingFakeProvider().transcribe(
            Path("unused"), source_reference="video.mp4", cancellation_requested=lambda: False
        )
    assert caught.value.detail.code == ErrorCode.PROVIDER_UNAVAILABLE


def test_faster_whisper_provider_maps_real_segment_shape_to_evidence(tmp_path: Path) -> None:
    model_dir = local_model(tmp_path / "model with spaces")
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake-wave")
    captured: dict[str, object] = {}

    class FakeModel:
        def transcribe(self, audio_path: str, **options: object) -> tuple[list[object], object]:
            captured.update({"audio_path": audio_path, **options})
            segment = SimpleNamespace(
                start=1.25,
                end=2.75,
                text="  evidence grounded speech  ",
                avg_logprob=-0.1,
                no_speech_prob=0.02,
            )
            info = SimpleNamespace(language="en", language_probability=0.97)
            return [segment], info

    provider = FasterWhisperProvider(
        model_dir,
        model_factory=lambda *_args, **_kwargs: FakeModel(),  # type: ignore[arg-type]
    )
    result = provider.transcribe(
        audio,
        source_reference="authorized.mp4",
        cancellation_requested=lambda: False,
    )

    assert captured["vad_filter"] is True
    assert result.language == "en"
    assert result.language_confidence == 0.97
    assert len(result.evidence_items) == 1
    item = result.evidence_items[0]
    assert (item.start_ms, item.end_ms) == (1250, 2750)
    assert item.text == "evidence grounded speech"
    assert item.source_reference == "authorized.mp4"
    assert item.provider == "local-faster-whisper"
    assert item.attributes["model_identifier"].startswith("local-ctranslate2:")
    assert item.attributes["vad_filter"] is True
    assert result.model_identifier == item.attributes["model_identifier"]


def test_faster_whisper_requires_complete_local_model_and_disables_download(
    tmp_path: Path,
) -> None:
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"wave")
    called = False

    def factory(*_args: object, **_kwargs: object) -> object:
        nonlocal called
        called = True
        raise AssertionError("factory must not run")

    for configured in (Path("tiny"), tmp_path / "missing", tmp_path / "empty"):
        if configured.name == "empty":
            configured.mkdir()
        provider = FasterWhisperProvider(configured, model_factory=factory)  # type: ignore[arg-type]
        with pytest.raises(VideoIntelligenceError) as caught:
            provider.transcribe(
                audio,
                source_reference="authorized.wav",
                cancellation_requested=lambda: False,
            )
        assert caught.value.detail.code == ErrorCode.PROVIDER_UNAVAILABLE
    assert called is False


def test_faster_whisper_passes_local_files_only_to_model_factory(tmp_path: Path) -> None:
    model_dir = local_model(tmp_path / "model")
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"wave")
    options: dict[str, object] = {}

    class FakeModel:
        def transcribe(self, _audio: str, **_options: object) -> tuple[list[object], object]:
            return [], SimpleNamespace(language="en", language_probability=0.9)

    def factory(_path: str, **kwargs: object) -> FakeModel:
        options.update(kwargs)
        return FakeModel()

    FasterWhisperProvider(model_dir, model_factory=factory).transcribe(
        audio,
        source_reference="authorized.wav",
        cancellation_requested=lambda: False,
    )
    assert options["local_files_only"] is True


def test_lazy_iteration_failure_is_not_reported_as_partial_success(tmp_path: Path) -> None:
    model_dir = local_model(tmp_path / "model")
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"wave")

    class FakeModel:
        def transcribe(self, _audio: str, **_options: object) -> tuple[object, object]:
            def segments() -> object:
                yield SimpleNamespace(
                    start=0.0,
                    end=1.0,
                    text="partial private speech",
                    avg_logprob=-0.1,
                    no_speech_prob=0.0,
                )
                raise RuntimeError("provider detail containing private speech")

            return segments(), SimpleNamespace(language="en", language_probability=0.9)

    provider = FasterWhisperProvider(
        model_dir,
        model_factory=lambda *_args, **_kwargs: FakeModel(),  # type: ignore[arg-type]
    )
    with pytest.raises(VideoIntelligenceError) as caught:
        provider.transcribe(
            audio,
            source_reference="authorized.wav",
            cancellation_requested=lambda: False,
        )
    assert caught.value.detail.code == ErrorCode.TRANSCRIPTION_FAILURE
    assert "private speech" not in caught.value.detail.message


def test_lazy_iteration_cancellation_closes_generator(tmp_path: Path) -> None:
    model_dir = local_model(tmp_path / "model")
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"wave")
    closed = False

    class FakeModel:
        def transcribe(self, _audio: str, **_options: object) -> tuple[object, object]:
            def segments() -> object:
                nonlocal closed
                try:
                    yield SimpleNamespace(
                        start=0.0,
                        end=1.0,
                        text="first",
                        avg_logprob=-0.1,
                        no_speech_prob=0.0,
                    )
                    yield SimpleNamespace(
                        start=1.0,
                        end=2.0,
                        text="second",
                        avg_logprob=-0.1,
                        no_speech_prob=0.0,
                    )
                finally:
                    closed = True

            return segments(), SimpleNamespace(language="en", language_probability=0.9)

    checks = iter((False, False, True))
    provider = FasterWhisperProvider(
        model_dir,
        model_factory=lambda *_args, **_kwargs: FakeModel(),  # type: ignore[arg-type]
    )
    with pytest.raises(TranscriptionCancelled):
        provider.transcribe(
            audio,
            source_reference="authorized.wav",
            cancellation_requested=lambda: next(checks, True),
        )
    assert closed is True


def test_non_monotonic_timestamps_are_rejected(tmp_path: Path) -> None:
    model_dir = local_model(tmp_path / "model")
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"wave")
    segments = [
        SimpleNamespace(start=2.0, end=3.0, text="later", avg_logprob=-0.1, no_speech_prob=0),
        SimpleNamespace(start=1.0, end=2.0, text="earlier", avg_logprob=-0.1, no_speech_prob=0),
    ]

    class FakeModel:
        def transcribe(self, _audio: str, **_options: object) -> tuple[list[object], object]:
            return segments, SimpleNamespace(language="en", language_probability=0.9)

    provider = FasterWhisperProvider(
        model_dir,
        model_factory=lambda *_args, **_kwargs: FakeModel(),  # type: ignore[arg-type]
    )
    with pytest.raises(VideoIntelligenceError) as caught:
        provider.transcribe(
            audio,
            source_reference="authorized.wav",
            cancellation_requested=lambda: False,
        )
    assert caught.value.detail.code == ErrorCode.MALFORMED_PROVIDER_OUTPUT
