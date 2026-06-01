"""Re-export the entry class so `from app.checks.ai.ai_llm_endpoint_discovery import LLMEndpointCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.ai_llm_endpoint_discovery.check import LLMEndpointCheck

__all__ = ["LLMEndpointCheck"]
