"""Re-export the entry class so `from app.checks.ai.token_cost_exhaustion import TokenCostExhaustionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.token_cost_exhaustion.check import TokenCostExhaustionCheck

__all__ = ["TokenCostExhaustionCheck"]
