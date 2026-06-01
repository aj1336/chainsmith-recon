"""Re-export the entry class so `from app.checks.ai.ai_tool_discovery import ToolDiscoveryCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_tool_discovery.check import ToolDiscoveryCheck

__all__ = ["ToolDiscoveryCheck"]
