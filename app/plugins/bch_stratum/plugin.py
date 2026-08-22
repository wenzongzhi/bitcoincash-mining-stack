from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from typing import Any

from app.core.models import LogEntry, Metric, PluginSummary, StatusSnapshot
from app.plugins.base import ProgramPlugin


SUPPORTED_SCHEMA_VERSION = 1
DEFAULT_STATUS_FILE = "runtime_status.json"
DEFAULT_STALE_SECONDS = 5.0
CACHE_TTL_SECONDS = 0.20


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def unix_to_datetime(value: Any) -> datetime | None:
    if not isinstance(value, (int, float)):
        return None
    try:
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def scaled_metric(
    *,
    key: str,
    label: str,
    value: float,
    scales: tuple[tuple[float, str], ...],
    decimals: int = 2,
) -> Metric:
    absolute = abs(value)
    divisor = 1.0
    unit = scales[-1][1]
    for threshold, candidate_unit in scales:
        if absolute >= threshold:
            divisor = threshold
            unit = candidate_unit
            break
    return Metric(
        key=key,
        label=label,
        value=round(value / divisor, decimals),
        unit=unit,
    )


def hashrate_metric(key: str, label: str, hashes_per_second: float) -> Metric:
    return scaled_metric(
        key=key,
        label=label,
        value=max(0.0, hashes_per_second),
        scales=(
            (1e15, "PH/s"),
            (1e12, "TH/s"),
            (1e9, "GH/s"),
            (1e6, "MH/s"),
            (1e3, "kH/s"),
            (1.0, "H/s"),
        ),
    )


def difficulty_metric(value: float) -> Metric:
    return scaled_metric(
        key="best_difficulty",
        label="Best Difficulty",
        value=max(0.0, value),
        scales=(
            (1e12, "T"),
            (1e9, "G"),
            (1e6, "M"),
            (1e3, "k"),
            (1.0, ""),
        ),
    )


class BitcoinCashStratumProxyPlugin(ProgramPlugin):
    """Read-only adapter for bitcoincash-stratum-proxy runtime_status.json.

    The dashboard never starts, stops, imports, calls, or writes to the mining
    proxy. The status file is the only integration point.
    """

    def __init__(self) -> None:
        configured_path = os.getenv("BCH_RUNTIME_STATUS_FILE", DEFAULT_STATUS_FILE)
        self._status_path = Path(configured_path).expanduser().resolve()
        self._stale_seconds = max(
            2.0,
            safe_float(
                os.getenv("BCH_STRATUM_STALE_SECONDS", str(DEFAULT_STALE_SECONDS)),
                DEFAULT_STALE_SECONDS,
            ),
        )

        self._cache_lock = asyncio.Lock()
        self._cache_loaded_monotonic = 0.0
        self._cache_data: dict[str, Any] | None = None
        self._cache_error: str | None = None
        self._cache_file_mtime_ns: int | None = None

        self._logs: deque[LogEntry] = deque(maxlen=200)
        self._last_health_signature: tuple[str, str | None] | None = None

    @property
    def summary(self) -> PluginSummary:
        return PluginSummary(
            plugin_id="bch-stratum-proxy",
            name="Bitcoin Cash Stratum Proxy",
            version="0.1.0",
            description=(
                "Read-only dashboard adapter for bitcoincash-stratum-proxy "
                "runtime_status.json."
            ),
        )

    def _append_log(self, level: str, message: str) -> None:
        self._logs.append(LogEntry(timestamp=utc_now(), level=level, message=message))

    def _record_health_change(self, state: str, detail: str | None) -> None:
        signature = (state, detail)
        if signature == self._last_health_signature:
            return
        self._last_health_signature = signature

        if state == "running":
            self._append_log("INFO", f"runtime status online: {self._status_path}")
        elif state == "stopped":
            self._append_log("WARNING", detail or "runtime status file not found")
        elif state == "unknown":
            self._append_log("WARNING", detail or "runtime status is stale")
        elif state == "error":
            self._append_log("ERROR", detail or "runtime status read failed")

    def _read_status_file_sync(self) -> tuple[dict[str, Any] | None, str | None, int | None]:
        try:
            stat = self._status_path.stat()
        except FileNotFoundError:
            return None, f"Status file not found: {self._status_path}", None
        except OSError as exc:
            return None, f"Cannot stat status file: {exc}", None

        try:
            with self._status_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            return None, f"Invalid runtime status JSON: {exc}", stat.st_mtime_ns
        except OSError as exc:
            return None, f"Cannot read runtime status file: {exc}", stat.st_mtime_ns

        if not isinstance(data, dict):
            return None, "Runtime status root must be a JSON object", stat.st_mtime_ns

        schema_version = data.get("schema_version")
        if schema_version != SUPPORTED_SCHEMA_VERSION:
            return (
                None,
                f"Unsupported runtime status schema_version={schema_version!r}; "
                f"expected {SUPPORTED_SCHEMA_VERSION}",
                stat.st_mtime_ns,
            )

        return data, None, stat.st_mtime_ns

    async def _load(self) -> tuple[dict[str, Any] | None, str | None]:
        now_mono = time.monotonic()
        if now_mono - self._cache_loaded_monotonic < CACHE_TTL_SECONDS:
            return self._cache_data, self._cache_error

        async with self._cache_lock:
            now_mono = time.monotonic()
            if now_mono - self._cache_loaded_monotonic < CACHE_TTL_SECONDS:
                return self._cache_data, self._cache_error

            data, error, mtime_ns = await asyncio.to_thread(self._read_status_file_sync)
            self._cache_data = data
            self._cache_error = error
            self._cache_file_mtime_ns = mtime_ns
            self._cache_loaded_monotonic = time.monotonic()
            return data, error

    def _file_age_seconds(self, data: dict[str, Any] | None) -> float | None:
        if not data:
            return None
        generated_at = data.get("generated_at")
        if not isinstance(generated_at, (int, float)):
            return None
        return max(0.0, time.time() - float(generated_at))

    def _health(
        self,
        data: dict[str, Any] | None,
        read_error: str | None,
    ) -> tuple[str, str | None]:
        if data is None:
            if read_error and read_error.startswith("Status file not found:"):
                return "stopped", read_error
            return "error", read_error or "Runtime status unavailable"

        age = self._file_age_seconds(data)
        if age is None:
            return "error", "runtime_status.json is missing a valid generated_at timestamp"
        if age > self._stale_seconds:
            return (
                "unknown",
                f"Runtime status is stale: last update {age:.1f}s ago "
                f"(threshold {self._stale_seconds:.1f}s)",
            )

        service = data.get("service")
        service_state = service.get("state") if isinstance(service, dict) else None
        if service_state in {"starting", "running", "stopping", "stopped", "error", "unknown"}:
            return str(service_state), None
        return "unknown", f"Unknown proxy service state: {service_state!r}"

    async def get_status(self) -> StatusSnapshot:
        data, read_error = await self._load()
        state, health_error = self._health(data, read_error)
        self._record_health_change(state, health_error)

        service = data.get("service", {}) if data else {}
        node = data.get("node", {}) if data else {}

        last_error = health_error
        # A BCHN/GBT failure does not mean the proxy process itself is dead, but
        # surfacing it here makes the current Phase-1 status card useful.
        if last_error is None and isinstance(node, dict) and not node.get("gbt_ok", False):
            node_error = node.get("last_gbt_error")
            if node_error:
                last_error = f"GBT: {node_error}"

        return StatusSnapshot(
            plugin_id=self.summary.plugin_id,
            state=state,  # type: ignore[arg-type]
            started_at=unix_to_datetime(service.get("started_at")),
            uptime_seconds=max(0.0, safe_float(service.get("uptime_seconds"))),
            pid=safe_int(service.get("pid"), 0) or None,
            last_error=last_error,
        )

    async def get_metrics(self) -> list[Metric]:
        data, _ = await self._load()
        if not data:
            return []

        stratum = data.get("stratum", {})
        node = data.get("node", {})
        chain = data.get("chain", {})
        summary = data.get("summary", {})
        hashrate = summary.get("hashrate", {}) if isinstance(summary, dict) else {}

        accepted = safe_int(summary.get("shares_accepted_total"))
        rejected = safe_int(summary.get("shares_rejected_total"))

        metrics: list[Metric] = [
            Metric(
                key="connected_miners",
                label="Connected Miners",
                value=safe_int(stratum.get("connected_miners")),
            ),
            hashrate_metric(
                "hashrate_5m",
                "Hashrate (5m)",
                safe_float(hashrate.get("5m_hs")),
            ),
            difficulty_metric(safe_float(summary.get("best_difficulty"))),
            Metric(
                key="template_height",
                label="Template Height",
                value=chain.get("template_height") if chain.get("template_height") is not None else "-",
            ),
            Metric(
                key="accepted_shares",
                label="Accepted Shares",
                value=accepted,
            ),
            Metric(
                key="rejected_shares",
                label="Rejected Shares",
                value=rejected,
            ),
            Metric(
                key="gbt",
                label="BCHN / GBT",
                value="OK" if node.get("gbt_ok", False) else "ERROR",
            ),
            Metric(
                key="template_transactions",
                label="Template Transactions",
                value=safe_int(chain.get("template_tx_count")),
            ),
        ]
        return metrics

    async def get_logs(self, limit: int = 100) -> list[LogEntry]:
        # Force a health read so state transitions appear even if only /logs is queried.
        data, read_error = await self._load()
        state, health_error = self._health(data, read_error)
        self._record_health_change(state, health_error)

        safe_limit = max(1, min(limit, 200))
        return list(self._logs)[-safe_limit:]

    async def get_data(self) -> dict[str, Any]:
        data, read_error = await self._load()
        if not data:
            return {
                "source": {
                    "type": "runtime_status_file",
                    "path": str(self._status_path),
                    "stale_after_seconds": self._stale_seconds,
                    "age_seconds": None,
                    "read_error": read_error,
                },
                "runtime": {},
            }

        return {
            "source": {
                "type": "runtime_status_file",
                "path": str(self._status_path),
                "stale_after_seconds": self._stale_seconds,
                "age_seconds": self._file_age_seconds(data),
                "read_error": read_error,
            },
            "runtime": data,
        }
