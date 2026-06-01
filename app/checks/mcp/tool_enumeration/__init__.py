"""Re-export the entry class so `from app.checks.mcp.tool_enumeration import MCPToolEnumerationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.tool_enumeration.check import MCPToolEnumerationCheck

__all__ = ["MCPToolEnumerationCheck"]
