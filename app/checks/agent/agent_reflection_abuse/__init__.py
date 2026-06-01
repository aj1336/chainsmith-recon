"""Re-export the entry class so `from app.checks.agent.agent_reflection_abuse import AgentReflectionAbuseCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_reflection_abuse.check import AgentReflectionAbuseCheck

__all__ = ["AgentReflectionAbuseCheck"]
