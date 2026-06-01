"""Re-export the entry class so `from app.checks.ai.ai_model_enumeration import ModelEnumerationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_model_enumeration.check import ModelEnumerationCheck

__all__ = ["ModelEnumerationCheck"]
