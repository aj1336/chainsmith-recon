"""Re-export the entry class so `from app.checks.cag.cag_semantic_threshold import SemanticThresholdCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_semantic_threshold.check import SemanticThresholdCheck

__all__ = ["SemanticThresholdCheck"]
