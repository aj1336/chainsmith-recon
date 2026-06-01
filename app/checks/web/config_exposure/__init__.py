"""Re-export the entry class so `from app.checks.web.config_exposure import ConfigExposureCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.config_exposure.check import ConfigExposureCheck

__all__ = ["ConfigExposureCheck"]
