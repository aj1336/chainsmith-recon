"""Re-export the entry class so `from app.checks.rag.rag_auth_bypass import RAGAuthBypassCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_auth_bypass.check import RAGAuthBypassCheck

__all__ = ["RAGAuthBypassCheck"]
