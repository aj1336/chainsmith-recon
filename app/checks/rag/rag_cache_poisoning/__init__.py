"""Re-export the entry class so `from app.checks.rag.rag_cache_poisoning import RAGCachePoisoningCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_cache_poisoning.check import RAGCachePoisoningCheck

__all__ = ["RAGCachePoisoningCheck"]
