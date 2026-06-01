"""Re-export the entry class so `from app.checks.network.ipv6_discovery import IPv6DiscoveryCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.ipv6_discovery.check import IPv6DiscoveryCheck

__all__ = ["IPv6DiscoveryCheck"]
