from __future__ import annotations

import json
from pathlib import Path

from video_intelligence.command_center.jobs import ProcessingJob, ProcessingJobList
from video_intelligence.command_center.models import (
    CommandCenterStatus,
    DoctorReport,
    StartResult,
    UpdateReport,
)
from video_intelligence.media.models import MediaProbeResult
from video_intelligence.models import AcquisitionDiagnostic, AnalysisResult, EvidenceItem

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    schemas = {
        "analysis-result.schema.json": AnalysisResult.model_json_schema(),
        "evidence-item.schema.json": EvidenceItem.model_json_schema(),
        "acquisition-diagnostic.schema.json": AcquisitionDiagnostic.model_json_schema(),
        "media-probe-result.schema.json": MediaProbeResult.model_json_schema(mode="serialization"),
        "command-center-status.schema.json": CommandCenterStatus.model_json_schema(),
        "command-center-start.schema.json": StartResult.model_json_schema(),
        "doctor-report.schema.json": DoctorReport.model_json_schema(),
        "update-report.schema.json": UpdateReport.model_json_schema(),
        "processing-job.schema.json": ProcessingJob.model_json_schema(mode="serialization"),
        "processing-job-list.schema.json": ProcessingJobList.model_json_schema(
            mode="serialization"
        ),
    }
    target = ROOT / "schemas"
    target.mkdir(exist_ok=True)
    for name, schema in schemas.items():
        (target / name).write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
