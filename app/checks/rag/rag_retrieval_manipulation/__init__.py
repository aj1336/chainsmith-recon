"""Re-export the entry class so `from app.checks.rag.rag_retrieval_manipulation import RAGRetrievalManipulationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_retrieval_manipulation.check import RAGRetrievalManipulationCheck

__all__ = ["RAGRetrievalManipulationCheck"]
