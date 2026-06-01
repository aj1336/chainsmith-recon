"""Re-export the entry class so `from app.checks.ai.function_calling_abuse import FunctionCallingAbuseCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.function_calling_abuse.check import FunctionCallingAbuseCheck

__all__ = ["FunctionCallingAbuseCheck"]
