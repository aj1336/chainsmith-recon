"""Re-export the entry class so `from app.checks.ai.ai_embedding_extraction import EmbeddingExtractionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_embedding_extraction.check import EmbeddingExtractionCheck

__all__ = ["EmbeddingExtractionCheck"]
