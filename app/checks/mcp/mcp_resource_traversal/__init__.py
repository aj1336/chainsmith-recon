"""Re-export the entry class so `from app.checks.mcp.mcp_resource_traversal import MCPResourceTraversalCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_resource_traversal.check import MCPResourceTraversalCheck

__all__ = ["MCPResourceTraversalCheck"]
