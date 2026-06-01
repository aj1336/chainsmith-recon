"""Re-export the entry class so `from app.checks.cag.cag_multi_layer_cache import MultiLayerCacheCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_multi_layer_cache.check import MultiLayerCacheCheck

__all__ = ["MultiLayerCacheCheck"]
