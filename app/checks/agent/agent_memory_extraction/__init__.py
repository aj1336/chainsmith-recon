"""Re-export the entry class so `from app.checks.agent.agent_memory_extraction import AgentMemoryExtractionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_memory_extraction.check import AgentMemoryExtractionCheck

__all__ = ["AgentMemoryExtractionCheck"]
