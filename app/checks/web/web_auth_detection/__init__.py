"""Re-export the entry class so `from app.checks.web.web_auth_detection import AuthDetectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_auth_detection.check import AuthDetectionCheck

__all__ = ["AuthDetectionCheck"]
