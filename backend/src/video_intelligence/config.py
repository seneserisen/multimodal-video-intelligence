from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class ProcessingProfile(StrEnum):
    FAST = "fast"
    BALANCED = "balanced"
    DEEP = "deep"
    SCREEN_HEAVY = "screen_heavy"
    VISUAL_DEMONSTRATION = "visual_demonstration"
    LECTURE = "lecture"
    ENGINEERING = "engineering"


class ImportanceWeights(BaseModel):
    model_config = ConfigDict(extra="forbid")

    base: float = 0.2
    modality: dict[str, float] = Field(
        default_factory=lambda: {
            "speech": 0.1,
            "screen_text": 0.2,
            "visual_event": 0.2,
            "audio_event": 0.1,
            "metadata": 0.0,
        }
    )
    contradiction_bonus: float = 0.4
    confirmation_bonus: float = 0.25
    uncertainty_penalty: float = 0.2


class PipelineConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    profile: ProcessingProfile = ProcessingProfile.BALANCED
    temporal_gap_ms: int = Field(default=5_000, ge=0)
    subtitle_overlap_threshold: float = Field(default=0.85, ge=0, le=1)
    importance_weights: ImportanceWeights = Field(default_factory=ImportanceWeights)
