"""Re-export the entry class so `from app.checks.rag.rag_adversarial_embedding import RAGAdversarialEmbeddingCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_adversarial_embedding.check import RAGAdversarialEmbeddingCheck

__all__ = ["RAGAdversarialEmbeddingCheck"]
