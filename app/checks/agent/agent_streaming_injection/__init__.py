"""Re-export the entry class so `from app.checks.agent.agent_streaming_injection import AgentStreamingInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_streaming_injection.check import AgentStreamingInjectionCheck

__all__ = ["AgentStreamingInjectionCheck"]
