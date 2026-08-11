from __future__ import annotations

import hashlib
import importlib
import json
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
        local_files_only: bool,
    ) -> WhisperModel: ...


def _default_model_factory(
    model_path: str,
    *,
    device: str,
    compute_type: str,
    local_files_only: bool,
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
    return model_class(
        model_path,
        device=device,
        compute_type=compute_type,
        local_files_only=local_files_only,
    )


REQUIRED_LOCAL_MODEL_FILES = ("model.bin", "config.json", "tokenizer.json")
SUPPORTED_DEVICES = frozenset({"auto", "cpu", "cuda"})
SUPPORTED_COMPUTE_TYPES = frozenset(
    {
        "auto",
        "default",
        "bfloat16",
        "float16",
        "float32",
        "int16",
        "int8",
        "int8_bfloat16",
        "int8_float16",
        "int8_float32",
    }
)


def validate_local_model_directory(model_path: Path) -> str | None:
    """Return a safe validation failure, or None for a complete local manifest."""
    resolved = model_path.expanduser().resolve(strict=False)
    if not resolved.is_dir():
        return "Configured model directory does not exist."
    for filename in REQUIRED_LOCAL_MODEL_FILES:
        candidate = resolved / filename
        if not candidate.is_file() or candidate.stat().st_size == 0:
            return f"Configured model directory is missing a non-empty {filename}."
    for filename in ("config.json", "tokenizer.json"):
        try:
            value = json.loads((resolved / filename).read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            return f"Configured model directory contains an invalid {filename}."
        if not isinstance(value, dict):
            return f"Configured model directory contains an invalid {filename}."
    return None


def _model_identifier(model_path: Path) -> str:
    config = (model_path / "config.json").read_bytes()
    size = (model_path / "model.bin").stat().st_size
    digest = hashlib.sha256(config + str(size).encode("ascii")).hexdigest()[:12]
    return f"local-ctranslate2:{digest}"


class FasterWhisperProvider:
    name = "local-faster-whisper"
    processing_version = "1"

    def __init__(
        self,
        model_path: Path,
        *,
        device: str = "cpu",
        compute_type: str = "int8",
        vad_filter: bool = True,
        model_factory: WhisperModelFactory = _default_model_factory,
    ) -> None:
        self.model_path = model_path.resolve(strict=False)
        self.device = device.casefold()
        self.compute_type = compute_type.casefold()
        self.vad_filter = vad_filter
        self._model_factory = model_factory
        self._model: WhisperModel | None = None

    def _load_model(self) -> WhisperModel:
        model_error = validate_local_model_directory(self.model_path)
        if model_error is not None:
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message=model_error,
                    safe_recovery_action=(
                        "Set VIDEO_INTELLIGENCE_WHISPER_MODEL to an existing local model directory."
                    ),
                )
            )
        if self.device not in SUPPORTED_DEVICES:
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message="The configured transcription device is unsupported.",
                    safe_recovery_action="Use auto, cpu, or cuda.",
                )
            )
        if self.compute_type not in SUPPORTED_COMPUTE_TYPES:
            raise VideoIntelligenceError(
                StructuredError(
                    code=ErrorCode.PROVIDER_UNAVAILABLE,
                    message="The configured transcription compute type is unsupported.",
                    safe_recovery_action="Choose a CTranslate2-supported compute type.",
                )
            )
        if self._model is None:
            self._model = self._model_factory(
                str(self.model_path),
                device=self.device,
                compute_type=self.compute_type,
                local_files_only=True,
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
                vad_filter=self.vad_filter,
                word_timestamps=False,
            )
            evidence: list[EvidenceItem] = []
            previous_start_ms = -1
            try:
                for index, segment in enumerate(segments):
                    if cancellation_requested():
                        raise TranscriptionCancelled
                    transcript = segment.text.strip()
                    if not transcript:
                        continue
                    start = float(segment.start)
                    end = float(segment.end)
                    if (
                        not math.isfinite(start)
                        or not math.isfinite(end)
                        or start < 0
                        or end < start
                    ):
                        raise VideoIntelligenceError(
                            StructuredError(
                                code=ErrorCode.MALFORMED_PROVIDER_OUTPUT,
                                message=(
                                    "The local provider returned an invalid transcript timestamp."
                                ),
                                retryable=True,
                                safe_recovery_action="Retry with a valid local model.",
                            )
                        )
                    start_ms = round(start * 1000)
                    end_ms = round(end * 1000)
                    if start_ms < previous_start_ms:
                        raise VideoIntelligenceError(
                            StructuredError(
                                code=ErrorCode.MALFORMED_PROVIDER_OUTPUT,
                                message=(
                                    "The local provider returned non-monotonic "
                                    "transcript timestamps."
                                ),
                                retryable=True,
                                safe_recovery_action="Retry with a valid local model.",
                            )
                        )
                    previous_start_ms = start_ms
                    confidence = min(1.0, max(0.0, math.exp(float(segment.avg_logprob))))
                    evidence.append(
                        EvidenceItem(
                            evidence_id=f"speech-{index:06d}",
                            modality=Modality.SPEECH,
                            evidence_type="transcript_segment",
                            start_ms=start_ms,
                            end_ms=end_ms,
                            text=transcript,
                            confidence=confidence,
                            source_reference=source_reference,
                            language=info.language or None,
                            provider=self.name,
                            processing_version=self.processing_version,
                            attributes={
                                "compute_type": self.compute_type,
                                "device": self.device,
                                "extraction_method": "faster-whisper-segment",
                                "model_identifier": _model_identifier(self.model_path),
                                "no_speech_probability": min(
                                    1.0, max(0.0, float(segment.no_speech_prob))
                                ),
                                "vad_filter": self.vad_filter,
                            },
                        )
                    )
                if cancellation_requested():
                    raise TranscriptionCancelled
            finally:
                close = getattr(segments, "close", None)
                if callable(close):
                    close()
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
            model_identifier=_model_identifier(self.model_path),
            device=self.device,
            compute_type=self.compute_type,
            vad_filter=self.vad_filter,
            evidence_items=evidence,
        )
