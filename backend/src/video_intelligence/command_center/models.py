from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from video_intelligence.models import SCHEMA_VERSION


class CommandCenterModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class RuntimeState(CommandCenterModel):
    schema_version: str = SCHEMA_VERSION
    pid: int = Field(gt=0)
    host: Literal["127.0.0.1"] = "127.0.0.1"
    port: int = Field(gt=0, le=65535)
    token: str = Field(min_length=32, repr=False)
    started_at: datetime
    version: str


class CommandCenterStatus(CommandCenterModel):
    schema_version: str = SCHEMA_VERSION
    running: bool
    pid: int | None = Field(default=None, gt=0)
    host: Literal["127.0.0.1"] = "127.0.0.1"
    port: int | None = Field(default=None, gt=0, le=65535)
    started_at: datetime | None = None
    version: str
    message: str
    active_jobs: int = Field(default=0, ge=0)
    completed_jobs: int = Field(default=0, ge=0)
    failed_jobs: int = Field(default=0, ge=0)
    max_upload_bytes: int | None = Field(default=None, gt=0)
    max_active_jobs: int | None = Field(default=None, gt=0)
    data_dir: str | None = None
    transcription_available: bool = False
    transcription_provider: str | None = None
    transcription_model_path: str | None = None
    transcription_status: str | None = None


class StartResult(CommandCenterModel):
    schema_version: str = SCHEMA_VERSION
    status: CommandCenterStatus
    dashboard_url: str
    already_running: bool = False


class DoctorCheck(CommandCenterModel):
    name: str
    status: Literal["ok", "warning", "error"]
    detail: str
    recovery_action: str | None = None


class DoctorReport(CommandCenterModel):
    schema_version: str = SCHEMA_VERSION
    ready: bool
    checks: list[DoctorCheck]


class UpdateReport(CommandCenterModel):
    schema_version: str = SCHEMA_VERSION
    repository: str
    branch: str
    upstream: str
    ahead: int = Field(ge=0)
    behind: int = Field(ge=0)
    applied: bool
    message: str
