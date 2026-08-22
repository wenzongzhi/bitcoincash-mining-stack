from __future__ import annotations

from app.core.registry import PluginRegistry
from app.plugins.bch_stratum.plugin import BitcoinCashStratumProxyPlugin
from app.plugins.dummy.plugin import DummyPlugin


def build_builtin_registry() -> PluginRegistry:
    registry = PluginRegistry()
    registry.register(DummyPlugin())
    registry.register(BitcoinCashStratumProxyPlugin())
    return registry
