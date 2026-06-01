"""Re-export the entry class so `from app.checks.agent.agent_state_manipulation import AgentStateManipulationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_state_manipulation.check import AgentStateManipulationCheck

__all__ = ["AgentStateManipulationCheck"]
