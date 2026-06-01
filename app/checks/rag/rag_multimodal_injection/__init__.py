"""Re-export the entry class so `from app.checks.rag.rag_multimodal_injection import RAGMultimodalInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_multimodal_injection.check import RAGMultimodalInjectionCheck

__all__ = ["RAGMultimodalInjectionCheck"]
