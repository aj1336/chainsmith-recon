"""Re-export the entry class so `from app.checks.cag.cag_cache_key_reverse import CacheKeyReverseCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_cache_key_reverse.check import CacheKeyReverseCheck

__all__ = ["CacheKeyReverseCheck"]
