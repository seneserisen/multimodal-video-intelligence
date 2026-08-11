from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from video_intelligence.errors import ErrorCode, VideoIntelligenceError
from video_intelligence.models import EvidenceItem
from video_intelligence.providers.fake import DeterministicFakeEvidenceProvider, FailingFakeProvider
from video_intelligence.transcription import FasterWhisperProvider


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
    model_dir = tmp_path / "model"
    model_dir.mkdir()
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
