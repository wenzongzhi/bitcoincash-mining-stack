from __future__ import annotations

import asyncio
import os
import random
from collections import deque
from datetime import datetime, timezone

from app.core.models import (
    ActionResult,
    ActionSpec,
    LogEntry,
    Metric,
    PluginSummary,
    StatusSnapshot,
)
from app.plugins.base import ProgramPlugin


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DummyPlugin(ProgramPlugin):
    """A fake long-running CLI program used to validate the framework."""

    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._started_at: datetime | None = None
        self._counter = 0
        self._temperature = 45.0
        self._last_error: str | None = None
        self._logs: deque[LogEntry] = deque(maxlen=500)

    @property
    def summary(self) -> PluginSummary:
        return PluginSummary(
            plugin_id="dummy",
            name="Dummy Worker",
            version="0.1.0",
            description="Framework demo plugin that simulates a long-running CLI worker.",
        )

    async def on_app_startup(self) -> None:
        await self._start_worker()

    async def on_app_shutdown(self) -> None:
        await self._stop_worker()

    async def _worker(self) -> None:
        try:
            while True:
                await asyncio.sleep(1.0)
                self._counter += 1
                self._temperature = round(random.uniform(42.0, 58.0), 1)
                if self._counter % 5 == 0:
                    self._append_log(
                        "INFO",
                        f"heartbeat counter={self._counter} temperature={self._temperature}C",
                    )
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # Defensive boundary for a background worker.
            self._last_error = str(exc)
            self._append_log("ERROR", f"worker failed: {exc}")
            raise

    async def _start_worker(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._last_error = None
        self._started_at = utc_now()
        self._task = asyncio.create_task(self._worker(), name="dummy-worker")
        self._append_log("INFO", "dummy worker started")

    async def _stop_worker(self) -> None:
        if self._task is None or self._task.done():
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._append_log("INFO", "dummy worker stopped")

    def _append_log(self, level: str, message: str) -> None:
        self._logs.append(LogEntry(timestamp=utc_now(), level=level, message=message))

    async def get_status(self) -> StatusSnapshot:
        running = self._task is not None and not self._task.done()
        uptime = 0.0
        if running and self._started_at is not None:
            uptime = max(0.0, (utc_now() - self._started_at).total_seconds())

        if self._last_error:
            state = "error"
        elif running:
            state = "running"
        else:
            state = "stopped"

        return StatusSnapshot(
            plugin_id=self.summary.plugin_id,
            state=state,
            started_at=self._started_at,
            uptime_seconds=uptime,
            pid=os.getpid(),
            last_error=self._last_error,
        )

    async def get_metrics(self) -> list[Metric]:
        return [
            Metric(key="counter", label="Counter", value=self._counter),
            Metric(
                key="temperature",
                label="Temperature",
                value=self._temperature,
                unit="°C",
            ),
        ]

    async def get_logs(self, limit: int = 100) -> list[LogEntry]:
        safe_limit = max(1, min(limit, 500))
        return list(self._logs)[-safe_limit:]

    async def get_actions(self) -> list[ActionSpec]:
        running = self._task is not None and not self._task.done()
        actions = [
            ActionSpec(
                key="reset_counter",
                label="Reset counter",
                description="Reset the demo counter to zero.",
            ),
            ActionSpec(
                key="add_log",
                label="Add test log",
                description="Insert a manual test log entry.",
            ),
        ]
        if running:
            actions.append(
                ActionSpec(
                    key="stop",
                    label="Stop worker",
                    description="Stop the dummy background task.",
                    dangerous=True,
                )
            )
            actions.append(
                ActionSpec(
                    key="restart",
                    label="Restart worker",
                    description="Restart the dummy background task.",
                    dangerous=True,
                )
            )
        else:
            actions.append(
                ActionSpec(
                    key="start",
                    label="Start worker",
                    description="Start the dummy background task.",
                )
            )
        return actions

    async def execute_action(self, action_key: str) -> ActionResult:
        if action_key == "reset_counter":
            self._counter = 0
            self._append_log("INFO", "counter reset from Web API")
            return ActionResult(success=True, message="Counter reset.")

        if action_key == "add_log":
            self._append_log("INFO", "manual test log from Web API")
            return ActionResult(success=True, message="Test log added.")

        if action_key == "start":
            await self._start_worker()
            return ActionResult(success=True, message="Worker started.")

        if action_key == "stop":
            await self._stop_worker()
            return ActionResult(success=True, message="Worker stopped.")

        if action_key == "restart":
            await self._stop_worker()
            await self._start_worker()
            return ActionResult(success=True, message="Worker restarted.")

        return await super().execute_action(action_key)
