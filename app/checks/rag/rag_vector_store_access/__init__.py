"""Re-export the entry class so `from app.checks.rag.rag_vector_store_access import RAGVectorStoreAccessCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_vector_store_access.check import RAGVectorStoreAccessCheck

__all__ = ["RAGVectorStoreAccessCheck"]
