"""Re-export the entry class so `from app.checks.web.web_sri import SRICheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_sri.check import SRICheck

__all__ = ["SRICheck"]
