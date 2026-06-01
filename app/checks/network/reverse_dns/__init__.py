"""Re-export the entry class so `from app.checks.network.reverse_dns import ReverseDnsCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.reverse_dns.check import ReverseDnsCheck

__all__ = ["ReverseDnsCheck"]
