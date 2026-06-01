"""Re-export the entry class so `from app.checks.ai.api_parameter_injection import APIParameterInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.api_parameter_injection.check import APIParameterInjectionCheck

__all__ = ["APIParameterInjectionCheck"]
