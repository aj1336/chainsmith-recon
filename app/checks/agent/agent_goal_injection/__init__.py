"""Re-export the entry class so `from app.checks.agent.agent_goal_injection import AgentGoalInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_goal_injection.check import AgentGoalInjectionCheck

__all__ = ["AgentGoalInjectionCheck"]
