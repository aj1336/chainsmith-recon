"""Re-export the entry class so `from app.checks.agent.agent_privilege_escalation import AgentPrivilegeEscalationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_privilege_escalation.check import AgentPrivilegeEscalationCheck

__all__ = ["AgentPrivilegeEscalationCheck"]
