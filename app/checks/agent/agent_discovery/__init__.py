"""Re-export the entry class so `from app.checks.agent.agent_discovery import AgentDiscoveryCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_discovery.check import AgentDiscoveryCheck

__all__ = ["AgentDiscoveryCheck"]
