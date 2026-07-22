from __future__ import annotations

import json
from pathlib import Path

from jsonschema import Draft202012Validator
from video_intelligence.command_center.models import (
    CommandCenterStatus,
    DoctorReport,
    StartResult,
    UpdateReport,
)
from video_intelligence.media.models import MediaProbeResult
from video_intelligence.models import AcquisitionDiagnostic, AnalysisResult, EvidenceItem


def test_checked_in_schemas_match_models() -> None:
    root = Path(__file__).parents[2]
    expected = {
        "analysis-result.schema.json": AnalysisResult.model_json_schema(),
        "evidence-item.schema.json": EvidenceItem.model_json_schema(),
        "acquisition-diagnostic.schema.json": AcquisitionDiagnostic.model_json_schema(),
        "media-probe-result.schema.json": MediaProbeResult.model_json_schema(mode="serialization"),
        "command-center-status.schema.json": CommandCenterStatus.model_json_schema(),
        "command-center-start.schema.json": StartResult.model_json_schema(),
        "doctor-report.schema.json": DoctorReport.model_json_schema(),
        "update-report.schema.json": UpdateReport.model_json_schema(),
    }
    for name, generated in expected.items():
        checked_in = json.loads((root / "schemas" / name).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(checked_in)
        assert checked_in == generated
