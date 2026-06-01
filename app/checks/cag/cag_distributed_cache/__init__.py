"""Re-export the entry class so `from app.checks.cag.cag_distributed_cache import DistributedCacheCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_distributed_cache.check import DistributedCacheCheck

__all__ = ["DistributedCacheCheck"]
