from __future__ import annotations

from app.core.models import ActionResult, PluginSnapshot, PluginSummary
from app.core.registry import PluginRegistry


class DashboardService:
    """Application/service layer between HTTP and program plugins."""

    def __init__(self, registry: PluginRegistry) -> None:
        self.registry = registry

    async def startup(self) -> None:
        for plugin in self.registry.all():
            await plugin.on_app_startup()

    async def shutdown(self) -> None:
        # Reverse order leaves room for dependency-aware plugins later.
        for plugin in reversed(self.registry.all()):
            await plugin.on_app_shutdown()

    def list_plugins(self) -> list[PluginSummary]:
        return [plugin.summary for plugin in self.registry.all()]

    async def snapshot(self, plugin_id: str, log_limit: int = 100) -> PluginSnapshot:
        plugin = self.registry.get(plugin_id)
        return PluginSnapshot(
            status=await plugin.get_status(),
            metrics=await plugin.get_metrics(),
            logs=await plugin.get_logs(log_limit),
            actions=await plugin.get_actions(),
            data=await plugin.get_data(),
        )

    async def execute_action(self, plugin_id: str, action_key: str) -> ActionResult:
        plugin = self.registry.get(plugin_id)
        return await plugin.execute_action(action_key)
