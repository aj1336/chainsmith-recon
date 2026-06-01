"""Re-export the entry class so `from app.checks.mcp.mcp_schema_leakage import ToolSchemaLeakageCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_schema_leakage.check import ToolSchemaLeakageCheck

__all__ = ["ToolSchemaLeakageCheck"]
