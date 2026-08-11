from __future__ import annotations

from pathlib import Path
from typing import Protocol

from video_intelligence.models import AnalysisResult, EvidenceItem
from video_intelligence.transcription import TranscriptionProvider as TranscriptionProvider


class OCRProvider(Protocol):
    @property
    def name(self) -> str: ...
    def extract_text(self, media_path: Path) -> list[EvidenceItem]: ...


class VisualAnalysisProvider(Protocol):
    @property
    def name(self) -> str: ...
    def analyze_visuals(self, media_path: Path) -> list[EvidenceItem]: ...


class AudioEventProvider(Protocol):
    @property
    def name(self) -> str: ...
    def detect_audio_events(self, media_path: Path) -> list[EvidenceItem]: ...


class SummarizationProvider(Protocol):
    @property
    def name(self) -> str: ...
    def summarize(self, result: AnalysisResult) -> str: ...
