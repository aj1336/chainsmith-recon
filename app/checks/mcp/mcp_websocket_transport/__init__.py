"""Re-export the entry class so `from app.checks.mcp.mcp_websocket_transport import WebSocketTransportCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_websocket_transport.check import WebSocketTransportCheck

__all__ = ["WebSocketTransportCheck"]
