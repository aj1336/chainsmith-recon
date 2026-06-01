"""Re-export the entry class so `from app.checks.cag.cag_cache_eviction import CacheEvictionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_cache_eviction.check import CacheEvictionCheck

__all__ = ["CacheEvictionCheck"]
