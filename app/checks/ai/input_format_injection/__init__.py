"""Re-export the entry class so `from app.checks.ai.input_format_injection import InputFormatInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.input_format_injection.check import InputFormatInjectionCheck

__all__ = ["InputFormatInjectionCheck"]
