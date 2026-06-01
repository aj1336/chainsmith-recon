"""Re-export the entry class so `from app.checks.agent.agent_trust_chain import AgentTrustChainCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_trust_chain.check import AgentTrustChainCheck

__all__ = ["AgentTrustChainCheck"]
