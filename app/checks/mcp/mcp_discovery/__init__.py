"""Re-export the entry class so `from app.checks.mcp.mcp_discovery import MCPDiscoveryCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_discovery.check import MCPDiscoveryCheck

__all__ = ["MCPDiscoveryCheck"]
