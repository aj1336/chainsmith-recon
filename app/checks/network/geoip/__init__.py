"""Re-export the entry class so `from app.checks.network.geoip import GeoIpCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.geoip.check import GeoIpCheck

__all__ = ["GeoIpCheck"]
