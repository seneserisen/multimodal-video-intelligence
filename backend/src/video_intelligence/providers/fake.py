from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
from pathlib import Path

from video_intelligence.errors import ErrorCode, StructuredError, VideoIntelligenceError
from video_intelligence.models import AnalysisResult, EvidenceItem
from video_intelligence.transcription import TranscriptionResult


class DeterministicFakeEvidenceProvider:
    def __init__(self, provider_name: str, evidence: list[EvidenceItem]) -> None:
        self._name = provider_name
        self._evidence = evidence

    @property
    def name(self) -> str:
        return self._name

    def transcribe(
        self,
        audio_path: Path,
        *,
        source_reference: str,
        cancellation_requested: Callable[[], bool],
    ) -> TranscriptionResult:
        return TranscriptionResult(
            provider=self.name,
            processing_version="fake-1",
            evidence_items=deepcopy(self._evidence),
        )

    def extract_text(self, media_path: Path) -> list[EvidenceItem]:
        return deepcopy(self._evidence)

    def analyze_visuals(self, media_path: Path) -> list[EvidenceItem]:
        return deepcopy(self._evidence)

    def detect_audio_events(self, media_path: Path) -> list[EvidenceItem]:
        return deepcopy(self._evidence)


class DeterministicFakeSummarizer:
    name = "deterministic-fake-summarizer"

    def summarize(self, result: AnalysisResult) -> str:
        item_count = len(result.evidence_items)
        segment_count = len(result.timeline_segments)
        return f"{item_count} evidence items across {segment_count} segments."


class FailingFakeProvider:
    name = "failing-fake-provider"

    def transcribe(
        self,
        audio_path: Path,
        *,
        source_reference: str,
        cancellation_requested: Callable[[], bool],
    ) -> TranscriptionResult:
        raise VideoIntelligenceError(
            StructuredError(
                code=ErrorCode.PROVIDER_UNAVAILABLE,
                message="The deterministic provider was configured to fail.",
                safe_recovery_action="Select another configured provider.",
            )
        )
