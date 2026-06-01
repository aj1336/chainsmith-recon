"""Re-export the entry class so `from app.checks.agent.agent_tool_abuse import AgentToolAbuseCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_tool_abuse.check import AgentToolAbuseCheck

__all__ = ["AgentToolAbuseCheck"]
