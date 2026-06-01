"""Re-export the entry class so `from app.checks.network.network_banner_grab import BannerGrabCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.network_banner_grab.check import BannerGrabCheck

__all__ = ["BannerGrabCheck"]
