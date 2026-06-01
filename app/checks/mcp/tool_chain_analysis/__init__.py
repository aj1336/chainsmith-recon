"""Re-export the entry class so `from app.checks.mcp.tool_chain_analysis import ToolChainAnalysisCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.tool_chain_analysis.check import ToolChainAnalysisCheck

__all__ = ["ToolChainAnalysisCheck"]
