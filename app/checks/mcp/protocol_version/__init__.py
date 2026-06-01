"""Re-export the entry class so `from app.checks.mcp.protocol_version import MCPProtocolVersionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.protocol_version.check import MCPProtocolVersionCheck

__all__ = ["MCPProtocolVersionCheck"]
