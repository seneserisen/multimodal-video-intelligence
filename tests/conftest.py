from __future__ import annotations

import json
from pathlib import Path

import pytest
from video_intelligence.fusion import analyze_evidence
from video_intelligence.models import AnalysisResult, EvidenceItem, Source

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def valid_result() -> AnalysisResult:
    payload = load_fixture("speech_only.json")
    evidence = [EvidenceItem.model_validate(item) for item in payload["evidence_items"]]  # type: ignore[union-attr]
    return analyze_evidence(evidence, source=Source(uri="fixture:speech_only"))
