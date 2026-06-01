"""Re-export the entry class so `from app.checks.web.hsts_preload import HSTSPreloadCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.hsts_preload.check import HSTSPreloadCheck

__all__ = ["HSTSPreloadCheck"]
