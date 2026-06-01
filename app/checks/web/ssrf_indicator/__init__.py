"""Re-export the entry class so `from app.checks.web.ssrf_indicator import SSRFIndicatorCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.ssrf_indicator.check import SSRFIndicatorCheck

__all__ = ["SSRFIndicatorCheck"]
