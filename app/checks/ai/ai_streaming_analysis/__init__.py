"""Re-export the entry class so `from app.checks.ai.ai_streaming_analysis import StreamingAnalysisCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_streaming_analysis.check import StreamingAnalysisCheck

__all__ = ["StreamingAnalysisCheck"]
