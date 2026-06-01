"""Re-export the entry class so `from app.checks.ai.ai_error_leakage import AIErrorLeakageCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_error_leakage.check import AIErrorLeakageCheck

__all__ = ["AIErrorLeakageCheck"]
