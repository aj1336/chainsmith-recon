"""Re-export the entry class so `from app.checks.cag.cag_cache_probe import CAGCacheProbeCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_cache_probe.check import CAGCacheProbeCheck

__all__ = ["CAGCacheProbeCheck"]
