from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


ProgramState = Literal[
    "starting",
    "running",
    "stopping",
    "stopped",
    "error",
    "unknown",
]


class PluginSummary(BaseModel):
    plugin_id: str
    name: str
    version: str = "0.1.0"
    description: str = ""


class StatusSnapshot(BaseModel):
    plugin_id: str
    state: ProgramState
    started_at: datetime | None = None
    uptime_seconds: float = Field(default=0.0, ge=0.0)
    pid: int | None = None
    last_error: str | None = None


class Metric(BaseModel):
    key: str
    label: str
    value: Any
    unit: str | None = None


class LogEntry(BaseModel):
    timestamp: datetime
    level: str = "INFO"
    message: str


class ActionSpec(BaseModel):
    key: str
    label: str
    description: str = ""
    dangerous: bool = False


class ActionResult(BaseModel):
    success: bool
    message: str
    data: dict[str, Any] = Field(default_factory=dict)


class PluginSnapshot(BaseModel):
    status: StatusSnapshot
    metrics: list[Metric]
    logs: list[LogEntry]
    actions: list[ActionSpec]
    # Plugin-specific structured payload. Existing plugins do not need to use it.
    data: dict[str, Any] = Field(default_factory=dict)
