from __future__ import annotations

from typing import Any

import pytest
from video_intelligence.config import PipelineConfig, ProcessingProfile
from video_intelligence.fusion import analyze_evidence
from video_intelligence.models import ClaimStatus, EvidenceItem, Source

from tests.conftest import load_fixture


def run_fixture(name: str, profile: ProcessingProfile = ProcessingProfile.BALANCED) -> Any:
    payload = load_fixture(name)
    evidence = [EvidenceItem.model_validate(item) for item in payload["evidence_items"]]
    return analyze_evidence(
        evidence,
        source=Source(uri=f"fixture:{name}"),
        config=PipelineConfig(profile=profile),
        title=str(payload["title"]),
    )


@pytest.mark.parametrize(
    "fixture",
    [
        "speech_only.json",
        "screen_only.json",
        "supplement_case.json",
        "visual_only.json",
        "missing_timestamp.json",
        "multiple_languages.json",
    ],
)
def test_core_synthetic_cases(fixture: str) -> None:
    result = run_fixture(fixture)
    assert result.evidence_items
    assert result.claims


def test_subtitle_is_deduplicated() -> None:
    result = run_fixture("subtitle_duplicate.json")
    assert [item.evidence_id for item in result.evidence_items] == ["speech-1"]
    assert "subtitle-1" in result.evidence_items[0].attributes["deduplicated_evidence_ids"]


def test_contradiction_is_explicit() -> None:
    result = run_fixture("contradiction_case.json")
    claim = next(claim for claim in result.claims if claim.status == ClaimStatus.CONTRADICTED)
    assert claim.supporting_evidence_ids == ["speech-1"]
    assert claim.contradicting_evidence_ids == ["screen-1"]
    assert claim.claim_id in result.contradictions


def test_cross_modal_confirmation_is_explicit() -> None:
    result = run_fixture("confirmation_case.json")
    claim = next(
        claim for claim in result.claims if claim.status == ClaimStatus.CROSS_MODAL_CONFIRMED
    )
    assert claim.supporting_evidence_ids == ["speech-1", "screen-1"]


def test_screen_only_fact_is_preserved() -> None:
    result = run_fixture("screen_only.json")
    assert result.important_screen_only_information[0]["evidence_ids"] == ["screen-1"]


def test_uncertainty_and_profile_are_preserved() -> None:
    result = run_fixture("uncertain_ocr.json", ProcessingProfile.SCREEN_HEAVY)
    assert result.uncertainties == ["ocr-1"]
    assert result.processing_profile == ProcessingProfile.SCREEN_HEAVY


def test_missing_timestamp_is_not_fabricated() -> None:
    result = run_fixture("missing_timestamp.json")
    assert result.duration_ms is None
    assert result.timeline_segments[0].start_ms is None


def test_multiple_languages_are_reported() -> None:
    assert run_fixture("multiple_languages.json").detected_languages == ["de", "en"]
