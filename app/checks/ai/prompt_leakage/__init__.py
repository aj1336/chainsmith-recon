"""Re-export the entry class so `from app.checks.ai.prompt_leakage import PromptLeakageCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.prompt_leakage.check import PromptLeakageCheck

__all__ = ["PromptLeakageCheck"]
