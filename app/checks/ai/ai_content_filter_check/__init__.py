"""Re-export the entry class so `from app.checks.ai.ai_content_filter_check import ContentFilterCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_content_filter_check.check import ContentFilterCheck

__all__ = ["ContentFilterCheck"]
