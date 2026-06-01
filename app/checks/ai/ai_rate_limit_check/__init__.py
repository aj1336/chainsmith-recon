"""Re-export the entry class so `from app.checks.ai.ai_rate_limit_check import RateLimitCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_rate_limit_check.check import RateLimitCheck

__all__ = ["RateLimitCheck"]
