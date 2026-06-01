"""Re-export the entry class so `from app.checks.agent.agent_callback_injection import AgentCallbackInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_callback_injection.check import AgentCallbackInjectionCheck

__all__ = ["AgentCallbackInjectionCheck"]
