"""Re-export the entry class so `from app.checks.ai.response_caching import ResponseCachingCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.response_caching.check import ResponseCachingCheck

__all__ = ["ResponseCachingCheck"]
