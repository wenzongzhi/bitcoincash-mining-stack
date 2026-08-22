from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DashboardConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    websocket_interval_seconds: float = 1.0
    default_log_limit: int = 100

    @classmethod
    def from_env(cls) -> "DashboardConfig":
        return cls(
            host=os.getenv("DASHBOARD_HOST", "127.0.0.1"),
            port=int(os.getenv("DASHBOARD_PORT", "8000")),
            websocket_interval_seconds=float(
                os.getenv("DASHBOARD_WS_INTERVAL", "1.0")
            ),
            default_log_limit=int(os.getenv("DASHBOARD_LOG_LIMIT", "100")),
        )
