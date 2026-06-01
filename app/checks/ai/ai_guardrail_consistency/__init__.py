"""Re-export the entry class so `from app.checks.ai.ai_guardrail_consistency import GuardrailConsistencyCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_guardrail_consistency.check import GuardrailConsistencyCheck

__all__ = ["GuardrailConsistencyCheck"]
