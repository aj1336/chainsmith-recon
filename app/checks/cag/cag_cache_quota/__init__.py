"""Re-export the entry class so `from app.checks.cag.cag_cache_quota import CacheQuotaCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_cache_quota.check import CacheQuotaCheck

__all__ = ["CacheQuotaCheck"]
