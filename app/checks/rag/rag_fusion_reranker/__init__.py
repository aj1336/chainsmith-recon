"""Re-export the entry class so `from app.checks.rag.rag_fusion_reranker import RAGFusionRerankerCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_fusion_reranker.check import RAGFusionRerankerCheck

__all__ = ["RAGFusionRerankerCheck"]
