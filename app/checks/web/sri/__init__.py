"""Re-export the entry class so `from app.checks.web.sri import SRICheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.sri.check import SRICheck

__all__ = ["SRICheck"]
