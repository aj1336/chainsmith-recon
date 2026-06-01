"""Re-export the entry class so `from app.checks.mcp.mcp_template_injection import ResourceTemplateInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_template_injection.check import ResourceTemplateInjectionCheck

__all__ = ["ResourceTemplateInjectionCheck"]
