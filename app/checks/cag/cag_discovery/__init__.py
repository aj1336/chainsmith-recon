"""Re-export the entry class so `from app.checks.cag.cag_discovery import CAGDiscoveryCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_discovery.check import CAGDiscoveryCheck

__all__ = ["CAGDiscoveryCheck"]
