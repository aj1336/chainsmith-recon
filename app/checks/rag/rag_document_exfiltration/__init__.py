"""Re-export the entry class so `from app.checks.rag.rag_document_exfiltration import RAGDocumentExfiltrationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.rag.rag_document_exfiltration.check import RAGDocumentExfiltrationCheck

__all__ = ["RAGDocumentExfiltrationCheck"]
