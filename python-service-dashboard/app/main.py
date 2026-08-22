from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import router as api_router
from app.core.config import DashboardConfig
from app.plugins.builtin import build_builtin_registry
from app.services.dashboard import DashboardService


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "web" / "static"


def create_app() -> FastAPI:
    config = DashboardConfig.from_env()
    service = DashboardService(build_builtin_registry())

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        app.state.config = config
        app.state.dashboard_service = service
        await service.startup()
        try:
            yield
        finally:
            await service.shutdown()

    app = FastAPI(
        title="Py Service Dashboard",
        version="0.1.0",
        description="Plugin-based Web dashboard for long-running CLI/service programs.",
        lifespan=lifespan,
    )
    app.include_router(api_router)
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    async def index() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()
