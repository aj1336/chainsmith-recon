"""Re-export the entry class so `from app.checks.network.dns_records import DnsRecordCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.dns_records.check import DnsRecordCheck

__all__ = ["DnsRecordCheck"]
