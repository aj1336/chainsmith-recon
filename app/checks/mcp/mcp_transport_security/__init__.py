"""Re-export the entry class so `from app.checks.mcp.mcp_transport_security import TransportSecurityCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_transport_security.check import TransportSecurityCheck

__all__ = ["TransportSecurityCheck"]
