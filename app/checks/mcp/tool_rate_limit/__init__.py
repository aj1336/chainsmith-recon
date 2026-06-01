"""Re-export the entry class so `from app.checks.mcp.tool_rate_limit import ToolRateLimitCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.tool_rate_limit.check import ToolRateLimitCheck

__all__ = ["ToolRateLimitCheck"]
