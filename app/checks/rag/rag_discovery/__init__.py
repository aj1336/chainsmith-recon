"""Re-export the entry class so `from app.checks.rag.rag_discovery import RAGDiscoveryCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_discovery.check import RAGDiscoveryCheck

__all__ = ["RAGDiscoveryCheck"]
