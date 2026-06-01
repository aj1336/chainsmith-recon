"""Re-export the entry class so `from app.checks.rag.rag_embedding_fingerprint import RAGEmbeddingFingerprintCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_embedding_fingerprint.check import RAGEmbeddingFingerprintCheck

__all__ = ["RAGEmbeddingFingerprintCheck"]
