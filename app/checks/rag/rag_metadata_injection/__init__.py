"""Re-export the entry class so `from app.checks.rag.rag_metadata_injection import RAGMetadataInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_metadata_injection.check import RAGMetadataInjectionCheck

__all__ = ["RAGMetadataInjectionCheck"]
