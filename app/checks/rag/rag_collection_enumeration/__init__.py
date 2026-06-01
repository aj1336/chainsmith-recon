"""Re-export the entry class so `from app.checks.rag.rag_collection_enumeration import RAGCollectionEnumerationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_collection_enumeration.check import RAGCollectionEnumerationCheck

__all__ = ["RAGCollectionEnumerationCheck"]
