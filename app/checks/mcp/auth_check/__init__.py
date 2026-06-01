"""Re-export the entry class so `from app.checks.mcp.auth_check import MCPAuthCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.auth_check.check import MCPAuthCheck

__all__ = ["MCPAuthCheck"]
