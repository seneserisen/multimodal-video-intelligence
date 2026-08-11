from __future__ import annotations

import importlib
import math
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Protocol, cast

from video_intelligence.errors import ErrorCode, StructuredError, VideoIntelligenceError
from video_intelligence.models import EvidenceItem, Modality
from video_intelligence.transcription.models import TranscriptionResult


class TranscriptionCancelled(Exception):
    """Raised when local speech recognition is cooperatively cancelled."""


class TranscriptionProvider(Protocol):
    @property
    def name(self) -> str: ...

    def transcribe(
        self,
        audio_path: Path,
        *,
        source_reference: str,
        cancellation_requested: Callable[[], bool],
    ) -> TranscriptionResult: ...


class WhisperSegment(Protocol):
    start: float
    end: float
    text: str
    avg_logprob: float
    no_speech_prob: float


class WhisperInfo(Protocol):
    language: str
    language_probability: float


class WhisperModel(Protocol):
    def transcribe(
        self,
        audio: str,
        *,
        beam_size: int,
        vad_filter: bool,
        word_timestamps: bool,
    ) -> tuple[Iterable[WhisperSegment], WhisperInfo]: ...


class WhisperModelFactory(Protocol):
    def __call__(
        self,
        model_path: str,
        *,
        device: str,
        compute_type: str,
    ) -> WhisperModel: ...


def _default_model_factory(
    model_path: str,
    *,
    device: str,
    compute_type: str,
) -> WhisperModel:
    try:
        module = importlib.import_module("faster_whisper")
        model_class = cast(WhisperModelFactory, module.WhisperModel)
    except (ImportError, AttributeError) as exc:
        raise VideoIntelligenceError(
            StructuredError(
                code=ErrorCode.PROVIDER_UNAVAILABLE,
                message="The optional local Faster-Whisper provider is not installed.",
                safe_recovery_action='Install the project with the "transcription" extra.',
            )
        ) from exc
    return model_class(model_path, device=device, compute_type=compute_type)


class FasterWhisperProvider:
    name = "local-faster-whisper"
    processing_version = "1"

    def __init__(
        self,
        model_path: Path,
        *,
        device: str = "cpu",
        compute_type: str = "int8",
        model_factory: WhisperModelFactory = _default_model_factory,
    ) -> None:
        self.model_path = model_path.resolve(strict=False)
        self.device = device
        self.compute_type = compute_type
        self._model_factory = model_factory
        self._model: WhisperModel | None = None

    def _load_model(self) -> WhisperModel:
        if not self.model_path.is_dir():
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message="The configured local transcription model directory does not exist.",
                    safe_recovery_action=(
                        "Set VIDEO_INTELLIGENCE_WHISPER_MODEL to an existing local model directory."
                    ),
                )
            )
        if self._model is None:
            self._model = self._model_factory(
                str(self.model_path),
                device=self.device,
                compute_type=self.compute_type,
            )
        return self._model

    def transcribe(
        self,
        audio_path: Path,
        *,
        source_reference: str,
        cancellation_requested: Callable[[], bool],
    ) -> TranscriptionResult:
        if cancellation_requested():
            raise TranscriptionCancelled
        try:
            segments, info = self._load_model().transcribe(
                str(audio_path.resolve(strict=True)),
                beam_size=5,
                vad_filter=True,
                word_timestamps=False,
            )
            evidence: list[EvidenceItem] = []
            for index, segment in enumerate(segments):
                if cancellation_requested():
                    raise TranscriptionCancelled
                transcript = segment.text.strip()
                if not transcript:
                    continue
                confidence = min(1.0, max(0.0, math.exp(float(segment.avg_logprob))))
                evidence.append(
                    EvidenceItem(
                        evidence_id=f"speech-{index:06d}",
                        modality=Modality.SPEECH,
                        evidence_type="transcript_segment",
                        start_ms=max(0, round(float(segment.start) * 1000)),
                        end_ms=max(0, round(float(segment.end) * 1000)),
                        text=transcript,
                        confidence=confidence,
                        source_reference=source_reference,
                        language=info.language or None,
                        provider=self.name,
                        processing_version=self.processing_version,
                        attributes={
                            "no_speech_probability": min(
                                1.0, max(0.0, float(segment.no_speech_prob))
                            )
                        },
                    )
                )
        except (TranscriptionCancelled, VideoIntelligenceError):
            raise
        except Exception as exc:
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.TRANSCRIPTION_FAILURE,
                    message="The local transcription provider failed safely.",
                    retryable=True,
                    safe_recovery_action="Check the local model and device settings, then retry.",
                )
            ) from exc
        return TranscriptionResult(
            provider=self.name,
            processing_version=self.processing_version,
            language=info.language or None,
            language_confidence=min(1.0, max(0.0, float(info.language_probability))),
            evidence_items=evidence,
        )
