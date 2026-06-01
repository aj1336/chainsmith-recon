"""Re-export the entry class so `from app.checks.ai.ai_framework_fingerprint import AIFrameworkFingerprintCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_framework_fingerprint.check import AIFrameworkFingerprintCheck

__all__ = ["AIFrameworkFingerprintCheck"]
