from __future__ import annotations

import pytest
from pydantic import ValidationError
from video_intelligence.models import AnalysisResult, Claim, EvidenceItem


def test_partial_timestamp_is_rejected() -> None:
    with pytest.raises(ValidationError, match="both be present or absent"):
        EvidenceItem(
            evidence_id="bad",
            modality="speech",
            evidence_type="transcript",
            start_ms=1,
            text="bad",
            confidence=1,
            provider="fake",
            processing_version="1",
        )


def test_analysis_rejects_unknown_evidence_reference(valid_result: AnalysisResult) -> None:
    payload = valid_result.model_dump()
    payload["claims"].append(
        Claim(
            claim_id="bad-claim",
            statement="bad",
            status="inferred",
            supporting_evidence_ids=["does-not-exist"],
            confidence=0.5,
        ).model_dump()
    )
    with pytest.raises(ValidationError, match="unknown evidence"):
        AnalysisResult.model_validate(payload)
