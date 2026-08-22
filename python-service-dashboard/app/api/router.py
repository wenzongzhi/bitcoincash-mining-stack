from __future__ import annotations

import asyncio

from fastapi import APIRouter, HTTPException, Query, Request, WebSocket, WebSocketDisconnect

from app.core.registry import PluginNotFoundError
from app.services.dashboard import DashboardService


router = APIRouter(prefix="/api")


def get_service(request: Request) -> DashboardService:
    return request.app.state.dashboard_service


def not_found(plugin_id: str) -> HTTPException:
    return HTTPException(status_code=404, detail=f"Unknown plugin: {plugin_id}")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/plugins")
async def list_plugins(request: Request):
    return get_service(request).list_plugins()


@router.get("/plugins/{plugin_id}/snapshot")
async def plugin_snapshot(
    plugin_id: str,
    request: Request,
    log_limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return await get_service(request).snapshot(plugin_id, log_limit)
    except PluginNotFoundError:
        raise not_found(plugin_id)


@router.get("/plugins/{plugin_id}/status")
async def plugin_status(plugin_id: str, request: Request):
    try:
        return await get_service(request).registry.get(plugin_id).get_status()
    except PluginNotFoundError:
        raise not_found(plugin_id)


@router.get("/plugins/{plugin_id}/metrics")
async def plugin_metrics(plugin_id: str, request: Request):
    try:
        return await get_service(request).registry.get(plugin_id).get_metrics()
    except PluginNotFoundError:
        raise not_found(plugin_id)


@router.get("/plugins/{plugin_id}/logs")
async def plugin_logs(
    plugin_id: str,
    request: Request,
    limit: int = Query(default=100, ge=1, le=500),
):
    try:
        return await get_service(request).registry.get(plugin_id).get_logs(limit)
    except PluginNotFoundError:
        raise not_found(plugin_id)


@router.get("/plugins/{plugin_id}/actions")
async def plugin_actions(plugin_id: str, request: Request):
    try:
        return await get_service(request).registry.get(plugin_id).get_actions()
    except PluginNotFoundError:
        raise not_found(plugin_id)


@router.post("/plugins/{plugin_id}/actions/{action_key}")
async def execute_action(plugin_id: str, action_key: str, request: Request):
    try:
        result = await get_service(request).execute_action(plugin_id, action_key)
    except PluginNotFoundError:
        raise not_found(plugin_id)

    if not result.success:
        raise HTTPException(status_code=400, detail=result.message)
    return result


@router.websocket("/ws/plugins/{plugin_id}")
async def plugin_websocket(websocket: WebSocket, plugin_id: str) -> None:
    service: DashboardService = websocket.app.state.dashboard_service
    interval: float = websocket.app.state.config.websocket_interval_seconds

    try:
        service.registry.get(plugin_id)
    except PluginNotFoundError:
        await websocket.close(code=1008, reason=f"Unknown plugin: {plugin_id}")
        return

    await websocket.accept()
    try:
        while True:
            snapshot = await service.snapshot(plugin_id, log_limit=30)
            await websocket.send_json(snapshot.model_dump(mode="json"))
            await asyncio.sleep(interval)
    except WebSocketDisconnect:
        return
