from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

from video_intelligence.errors import StructuredError
from video_intelligence.models import SCHEMA_VERSION

StreamType = Literal["video", "audio", "subtitle", "data", "attachment", "unknown"]


class MediaModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MediaValidationConfig(MediaModel):
    max_file_size_bytes: int = Field(default=5 * 1024**3, gt=0)
    max_duration_ms: int = Field(default=4 * 60 * 60 * 1000, gt=0)
    require_audio: bool = False
    allowed_extensions: frozenset[str] = frozenset(
        {".avi", ".m4v", ".mkv", ".mov", ".mp4", ".webm"}
    )
    allowed_video_codecs: frozenset[str] = frozenset({"av1", "h264", "hevc", "mpeg4", "vp8", "vp9"})
    allowed_audio_codecs: frozenset[str] = frozenset(
        {"aac", "ac3", "flac", "mp3", "opus", "pcm_s16le", "vorbis"}
    )
    subprocess_timeout_seconds: float = Field(default=30.0, gt=0, le=300)


class MediaStream(MediaModel):
    index: int = Field(ge=0)
    stream_type: StreamType
    codec_name: str | None = None
    duration_ms: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    frame_rate: float | None = Field(default=None, gt=0)
    sample_rate_hz: int | None = Field(default=None, gt=0)
    channels: int | None = Field(default=None, gt=0)


class MediaProbeResult(MediaModel):
    schema_version: str = SCHEMA_VERSION
    path: str
    file_size_bytes: int = Field(ge=0)
    format_names: list[str]
    duration_ms: int | None = Field(default=None, ge=0)
    streams: list[MediaStream]
    warnings: list[str] = Field(default_factory=list)
    errors: list[StructuredError] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_video(self) -> bool:
        return any(stream.stream_type == "video" for stream in self.streams)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def has_audio(self) -> bool:
        return any(stream.stream_type == "audio" for stream in self.streams)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def valid(self) -> bool:
        return not self.errors
