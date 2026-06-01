"""Re-export the entry class so `from app.checks.network.network_tls_analysis import TlsAnalysisCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.network_tls_analysis.check import TlsAnalysisCheck

__all__ = ["TlsAnalysisCheck"]
