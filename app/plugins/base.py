from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.models import (
    ActionResult,
    ActionSpec,
    LogEntry,
    Metric,
    PluginSummary,
    StatusSnapshot,
)


class ProgramPlugin(ABC):
    """Contract implemented by every program that wants a Web dashboard.

    FastAPI depends only on this abstraction. A plugin may wrap an embedded
    Python service, a subprocess/EXE, an RPC service, or a log/status file.
    """

    @property
    @abstractmethod
    def summary(self) -> PluginSummary:
        raise NotImplementedError

    async def on_app_startup(self) -> None:
        """Optional lifecycle hook called once when FastAPI starts."""

    async def on_app_shutdown(self) -> None:
        """Optional lifecycle hook called once when FastAPI shuts down."""

    @abstractmethod
    async def get_status(self) -> StatusSnapshot:
        raise NotImplementedError

    @abstractmethod
    async def get_metrics(self) -> list[Metric]:
        raise NotImplementedError

    @abstractmethod
    async def get_logs(self, limit: int = 100) -> list[LogEntry]:
        raise NotImplementedError

    async def get_actions(self) -> list[ActionSpec]:
        return []

    async def get_data(self) -> dict[str, Any]:
        """Optional plugin-specific structured data for richer UIs.

        This keeps the common status/metrics/logs/actions contract stable while
        allowing plugins to expose tables, histories, peer lists, miner lists,
        etc. Existing plugins automatically return an empty object.
        """
        return {}

    async def execute_action(self, action_key: str) -> ActionResult:
        return ActionResult(
            success=False,
            message=f"Unsupported action: {action_key}",
        )
