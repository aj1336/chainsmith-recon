"""Re-export the entry class so `from app.checks.cag.cag_provider_caching import ProviderCachingCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_provider_caching.check import ProviderCachingCheck

__all__ = ["ProviderCachingCheck"]
