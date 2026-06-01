"""Re-export the entry class so `from app.checks.mcp.mcp_sampling_abuse import MCPSamplingAbuseCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_sampling_abuse.check import MCPSamplingAbuseCheck

__all__ = ["MCPSamplingAbuseCheck"]
