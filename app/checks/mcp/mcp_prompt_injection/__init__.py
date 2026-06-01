"""Re-export the entry class so `from app.checks.mcp.mcp_prompt_injection import MCPPromptInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_prompt_injection.check import MCPPromptInjectionCheck

__all__ = ["MCPPromptInjectionCheck"]
