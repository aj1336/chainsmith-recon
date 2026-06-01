"""Re-export the entry class so `from app.checks.mcp.mcp_undeclared_capabilities import UndeclaredCapabilityCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_undeclared_capabilities.check import UndeclaredCapabilityCheck

__all__ = ["UndeclaredCapabilityCheck"]
