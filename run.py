from __future__ import annotations

import uvicorn

from app.core.config import DashboardConfig


if __name__ == "__main__":
    config = DashboardConfig.from_env()
    uvicorn.run(
        "app.main:app",
        host=config.host,
        port=config.port,
        reload=False,
    )
