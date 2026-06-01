"""Re-export the entry class so `from app.checks.rag.rag_indirect_injection import RAGIndirectInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_indirect_injection.check import RAGIndirectInjectionCheck

__all__ = ["RAGIndirectInjectionCheck"]
