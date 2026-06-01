"""Re-export the entry class so `from app.checks.rag.rag_cross_collection import RAGCrossCollectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_cross_collection.check import RAGCrossCollectionCheck

__all__ = ["RAGCrossCollectionCheck"]
