"""Re-export the entry class so `from app.checks.network.dns_enumeration import DnsEnumerationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.dns_enumeration.check import DnsEnumerationCheck

__all__ = ["DnsEnumerationCheck"]
