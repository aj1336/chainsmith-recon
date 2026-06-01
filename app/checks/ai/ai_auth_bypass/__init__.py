"""Re-export the entry class so `from app.checks.ai.ai_auth_bypass import AuthBypassCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_auth_bypass.check import AuthBypassCheck

__all__ = ["AuthBypassCheck"]
