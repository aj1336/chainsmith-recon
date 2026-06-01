"""Re-export the entry class so `from app.checks.rag.rag_corpus_poisoning import RAGCorpusPoisoningCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_corpus_poisoning.check import RAGCorpusPoisoningCheck

__all__ = ["RAGCorpusPoisoningCheck"]
