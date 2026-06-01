"""Re-export the entry class so `from app.checks.cag.cag_ttl_mapping import TTLMappingCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_ttl_mapping.check import TTLMappingCheck

__all__ = ["TTLMappingCheck"]
