from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Self
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from video_intelligence.config import ProcessingProfile
from video_intelligence.errors import StructuredError

SCHEMA_VERSION = "1.0.0"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class Platform(StrEnum):
    YOUTUBE = "youtube"
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    LOCAL = "local"
    SYNTHETIC = "synthetic"
    UNKNOWN = "unknown"


class Source(StrictModel):
    schema_version: str = SCHEMA_VERSION
    uri: str
    kind: str = "synthetic_evidence"
    authorized: bool = True


class AttemptOutcome(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"


class AcquisitionAttempt(StrictModel):
    method: str
    outcome: AttemptOutcome
    detail: str


class AcquisitionDiagnostic(StrictModel):
    schema_version: str = SCHEMA_VERSION
    platform: Platform
    attempts: list[AcquisitionAttempt]
    terminal_failure_reason: str | None = None
    browser_played: bool | None = None
    audio_detected: bool | None = None
    valid_video_frames_detected: bool | None = None
    safest_recovery_action: str | None = None


class Modality(StrEnum):
    SPEECH = "speech"
    SCREEN_TEXT = "screen_text"
    VISUAL_EVENT = "visual_event"
    AUDIO_EVENT = "audio_event"
    METADATA = "metadata"


class BoundingBox(StrictModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    width: float = Field(gt=0, le=1)
    height: float = Field(gt=0, le=1)

    @model_validator(mode="after")
    def within_frame(self) -> Self:
        if self.x + self.width > 1 or self.y + self.height > 1:
            raise ValueError("bounding box must fit within the normalized frame")
        return self


class EvidenceItem(StrictModel):
    schema_version: str = SCHEMA_VERSION
    evidence_id: str
    modality: Modality
    evidence_type: str
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    text: str | None = None
    description: str | None = None
    confidence: float = Field(ge=0, le=1)
    source_reference: str | None = None
    frame_reference: str | None = None
    bounding_box: BoundingBox | None = None
    language: str | None = None
    entities: list[str] = Field(default_factory=list)
    attributes: dict[str, Any] = Field(default_factory=dict)
    uncertainty: str | None = None
    provider: str
    processing_version: str

    @model_validator(mode="after")
    def valid_interval_and_content(self) -> Self:
        if (self.start_ms is None) != (self.end_ms is None):
            raise ValueError("start_ms and end_ms must both be present or absent")
        if self.start_ms is not None and self.end_ms is not None and self.end_ms < self.start_ms:
            raise ValueError("end_ms must be greater than or equal to start_ms")
        if not self.text and not self.description:
            raise ValueError("evidence requires text or description")
        return self


class ClaimStatus(StrEnum):
    EXPLICITLY_SPOKEN = "explicitly_spoken"
    SHOWN_ON_SCREEN = "shown_on_screen"
    VISUALLY_OBSERVED = "visually_observed"
    DEMONSTRATED = "demonstrated"
    CROSS_MODAL_CONFIRMED = "cross_modal_confirmed"
    SPEAKER_OPINION = "speaker_opinion"
    UNSUPPORTED_CLAIM = "unsupported_claim"
    CONTRADICTED = "contradicted"
    INFERRED = "inferred"
    UNCERTAIN = "uncertain"


class Claim(StrictModel):
    schema_version: str = SCHEMA_VERSION
    claim_id: str
    statement: str
    status: ClaimStatus
    supporting_evidence_ids: list[str] = Field(default_factory=list)
    contradicting_evidence_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0, le=1)
    verification_note: str | None = None


class TimelineSegment(StrictModel):
    schema_version: str = SCHEMA_VERSION
    segment_id: str
    start_ms: int | None = Field(default=None, ge=0)
    end_ms: int | None = Field(default=None, ge=0)
    topic: str
    speech_evidence: list[str] = Field(default_factory=list)
    screen_text_evidence: list[str] = Field(default_factory=list)
    visual_evidence: list[str] = Field(default_factory=list)
    audio_evidence: list[str] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list)
    claims: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    importance_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)


class CoverageReport(StrictModel):
    schema_version: str = SCHEMA_VERSION
    evidence_count_by_modality: dict[str, int]
    timed_evidence_ratio: float = Field(ge=0, le=1)
    uncertain_evidence_count: int = Field(ge=0)
    acquisition_complete: bool
    analysis_complete: bool
    notes: list[str] = Field(default_factory=list)


class AnalysisResult(StrictModel):
    schema_version: str = SCHEMA_VERSION
    analysis_id: str = Field(default_factory=lambda: str(uuid4()))
    source: Source
    platform: Platform
    title: str
    duration_ms: int | None = Field(default=None, ge=0)
    detected_languages: list[str]
    processing_profile: ProcessingProfile
    acquisition_diagnostic: AcquisitionDiagnostic
    one_sentence_takeaway: str
    concise_summary: str
    detailed_summary: str
    chapters: list[dict[str, Any]] = Field(default_factory=list)
    key_points: list[dict[str, Any]] = Field(default_factory=list)
    important_screen_only_information: list[dict[str, Any]] = Field(default_factory=list)
    visual_demonstrations: list[dict[str, Any]] = Field(default_factory=list)
    technical_values: list[dict[str, Any]] = Field(default_factory=list)
    people_organizations: list[str] = Field(default_factory=list)
    products_tools_technologies: list[str] = Field(default_factory=list)
    action_items: list[dict[str, Any]] = Field(default_factory=list)
    claims: list[Claim]
    contradictions: list[str]
    uncertainties: list[str]
    evidence_items: list[EvidenceItem]
    timeline_segments: list[TimelineSegment]
    coverage_report: CoverageReport
    processing_warnings: list[str] = Field(default_factory=list)
    errors: list[StructuredError] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def references_exist(self) -> Self:
        evidence_ids = [item.evidence_id for item in self.evidence_items]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("evidence IDs must be unique")
        known_evidence = set(evidence_ids)
        claim_ids = [claim.claim_id for claim in self.claims]
        if len(claim_ids) != len(set(claim_ids)):
            raise ValueError("claim IDs must be unique")
        known_claims = set(claim_ids)
        for claim in self.claims:
            refs = set(claim.supporting_evidence_ids + claim.contradicting_evidence_ids)
            if missing := refs - known_evidence:
                raise ValueError(f"claim {claim.claim_id} has unknown evidence: {sorted(missing)}")
        for segment in self.timeline_segments:
            refs = set(
                segment.speech_evidence
                + segment.screen_text_evidence
                + segment.visual_evidence
                + segment.audio_evidence
            )
            if missing := refs - known_evidence:
                raise ValueError(
                    f"segment {segment.segment_id} has unknown evidence: {sorted(missing)}"
                )
            if missing_claims := set(segment.claims + segment.contradictions) - known_claims:
                raise ValueError(
                    f"segment {segment.segment_id} has unknown claims: {sorted(missing_claims)}"
                )
        return self
