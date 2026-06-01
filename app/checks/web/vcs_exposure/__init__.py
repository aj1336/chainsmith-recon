"""Re-export the entry class so `from app.checks.web.vcs_exposure import VCSExposureCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.vcs_exposure.check import VCSExposureCheck

__all__ = ["VCSExposureCheck"]
