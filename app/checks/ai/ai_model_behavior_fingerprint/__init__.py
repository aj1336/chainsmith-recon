"""Re-export the entry class so `from app.checks.ai.ai_model_behavior_fingerprint import ModelBehaviorFingerprintCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_model_behavior_fingerprint.check import ModelBehaviorFingerprintCheck

__all__ = ["ModelBehaviorFingerprintCheck"]
