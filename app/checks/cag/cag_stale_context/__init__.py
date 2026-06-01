"""Re-export the entry class so `from app.checks.cag.cag_stale_context import StaleContextCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_stale_context.check import StaleContextCheck

__all__ = ["StaleContextCheck"]
