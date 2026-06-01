"""Re-export the entry class so `from app.checks.network.network_wildcard_dns import WildcardDnsCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.network_wildcard_dns.check import WildcardDnsCheck

__all__ = ["WildcardDnsCheck"]
