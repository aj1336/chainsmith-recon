"""Re-export the entry class so `from app.checks.ai.ai_context_window_check import ContextWindowCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_context_window_check.check import ContextWindowCheck

__all__ = ["ContextWindowCheck"]
