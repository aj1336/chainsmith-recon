"""Re-export the entry class so `from app.checks.web.debug_endpoints import DebugEndpointCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.debug_endpoints.check import DebugEndpointCheck

__all__ = ["DebugEndpointCheck"]
