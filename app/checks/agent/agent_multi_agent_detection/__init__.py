"""Re-export the entry class so `from app.checks.agent.agent_multi_agent_detection import AgentMultiAgentDetectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_multi_agent_detection.check import AgentMultiAgentDetectionCheck

__all__ = ["AgentMultiAgentDetectionCheck"]
