"""Re-export the entry class so `from app.checks.cag.cag_cross_user_leakage import CrossUserLeakageCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_cross_user_leakage.check import CrossUserLeakageCheck

__all__ = ["CrossUserLeakageCheck"]
