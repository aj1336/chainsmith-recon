"""Re-export the entry class so `from app.checks.agent.agent_context_overflow import AgentContextOverflowCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_context_overflow.check import AgentContextOverflowCheck

__all__ = ["AgentContextOverflowCheck"]
