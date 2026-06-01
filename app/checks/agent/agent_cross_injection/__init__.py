"""Re-export the entry class so `from app.checks.agent.agent_cross_injection import AgentCrossInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_cross_injection.check import AgentCrossInjectionCheck

__all__ = ["AgentCrossInjectionCheck"]
