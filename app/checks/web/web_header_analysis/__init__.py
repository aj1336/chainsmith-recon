"""Re-export the entry class so `from app.checks.web.web_header_analysis import HeaderAnalysisCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_header_analysis.check import HeaderAnalysisCheck

__all__ = ["HeaderAnalysisCheck"]
