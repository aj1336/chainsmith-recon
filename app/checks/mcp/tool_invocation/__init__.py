"""Re-export the entry class so `from app.checks.mcp.tool_invocation import MCPToolInvocationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.tool_invocation.check import MCPToolInvocationCheck

__all__ = ["MCPToolInvocationCheck"]
