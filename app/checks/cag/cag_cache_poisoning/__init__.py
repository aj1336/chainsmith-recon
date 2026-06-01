"""Re-export the entry class so `from app.checks.cag.cag_cache_poisoning import CachePoisoningCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_cache_poisoning.check import CachePoisoningCheck

__all__ = ["CachePoisoningCheck"]
