"""Re-export the entry class so `from app.checks.cag.cag_cache_warming import CacheWarmingCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_cache_warming.check import CacheWarmingCheck

__all__ = ["CacheWarmingCheck"]
