"""Re-export the entry class so `from app.checks.network.network_traceroute import TracerouteCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.network_traceroute.check import TracerouteCheck

__all__ = ["TracerouteCheck"]
