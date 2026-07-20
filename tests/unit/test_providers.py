from __future__ import annotations

from pathlib import Path

import pytest
from video_intelligence.errors import ErrorCode, VideoIntelligenceError
from video_intelligence.models import EvidenceItem
from video_intelligence.providers.fake import DeterministicFakeEvidenceProvider, FailingFakeProvider


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
    first = provider.transcribe(Path("unused"))
    second = provider.transcribe(Path("unused"))
    assert first == second
    assert first is not second


def test_provider_failure_is_structured() -> None:
    with pytest.raises(VideoIntelligenceError) as caught:
        FailingFakeProvider().transcribe(Path("unused"))
    assert caught.value.detail.code == ErrorCode.PROVIDER_UNAVAILABLE
