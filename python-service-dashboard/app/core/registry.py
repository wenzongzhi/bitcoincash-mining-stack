from __future__ import annotations

from app.plugins.base import ProgramPlugin


class PluginNotFoundError(KeyError):
    pass


class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, ProgramPlugin] = {}

    def register(self, plugin: ProgramPlugin) -> None:
        plugin_id = plugin.summary.plugin_id
        if plugin_id in self._plugins:
            raise ValueError(f"Duplicate plugin_id: {plugin_id}")
        self._plugins[plugin_id] = plugin

    def get(self, plugin_id: str) -> ProgramPlugin:
        try:
            return self._plugins[plugin_id]
        except KeyError as exc:
            raise PluginNotFoundError(plugin_id) from exc

    def all(self) -> list[ProgramPlugin]:
        return list(self._plugins.values())
