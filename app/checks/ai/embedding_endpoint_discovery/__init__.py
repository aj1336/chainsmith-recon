"""Re-export the entry class so `from app.checks.ai.embedding_endpoint_discovery import EmbeddingEndpointCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.embedding_endpoint_discovery.check import EmbeddingEndpointCheck

__all__ = ["EmbeddingEndpointCheck"]
