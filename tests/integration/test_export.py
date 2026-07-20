from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from video_intelligence.export import export_result
from video_intelligence.models import AnalysisResult


def test_json_and_markdown_export_validate(tmp_path: Path, valid_result: AnalysisResult) -> None:
    json_path, markdown_path = export_result(valid_result, tmp_path)
    schema_path = Path(__file__).parents[2] / "schemas" / "analysis-result.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(json.loads(json_path.read_text(encoding="utf-8")))
    assert "evidence: speech-1" in markdown_path.read_text(encoding="utf-8")


def test_export_surfaces_cleanup_or_write_failure(
    tmp_path: Path, valid_result: AnalysisResult, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_write(self: Path, *_args: object, **_kwargs: object) -> int:
        raise OSError("simulated cleanup/write failure")

    monkeypatch.setattr(Path, "write_text", fail_write)
    with pytest.raises(OSError, match="simulated"):
        export_result(valid_result, tmp_path)
