"""Re-export the entry class so `from app.checks.network.whois_lookup import WhoisLookupCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.whois_lookup.check import WhoisLookupCheck

__all__ = ["WhoisLookupCheck"]
