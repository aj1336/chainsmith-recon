"""Re-export the entry class so `from app.checks.mcp.mcp_shadow_tool_detection import ShadowToolDetectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_shadow_tool_detection.check import ShadowToolDetectionCheck

__all__ = ["ShadowToolDetectionCheck"]
