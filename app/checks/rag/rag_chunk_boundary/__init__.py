"""Re-export the entry class so `from app.checks.rag.rag_chunk_boundary import RAGChunkBoundaryCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_chunk_boundary.check import RAGChunkBoundaryCheck

__all__ = ["RAGChunkBoundaryCheck"]
