"""Re-export the entry class so `from app.checks.agent.agent_framework_version import AgentFrameworkVersionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.agent.agent_framework_version.check import AgentFrameworkVersionCheck

__all__ = ["AgentFrameworkVersionCheck"]
