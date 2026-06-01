"""Re-export the entry class so `from app.checks.ai.model_info_check import ModelInfoCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.model_info_check.check import ModelInfoCheck

__all__ = ["ModelInfoCheck"]
