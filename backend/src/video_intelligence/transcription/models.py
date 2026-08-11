from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from video_intelligence.models import SCHEMA_VERSION, EvidenceItem


class TranscriptionResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str = SCHEMA_VERSION
    provider: str
    processing_version: str
    language: str | None = None
    language_confidence: float | None = Field(default=None, ge=0, le=1)
    model_identifier: str | None = None
    device: str | None = None
    compute_type: str | None = None
    vad_filter: bool | None = None
    evidence_items: list[EvidenceItem]
