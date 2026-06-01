"""Re-export the entry class so `from app.checks.mcp.mcp_notification_injection import MCPNotificationInjectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.mcp_notification_injection.check import MCPNotificationInjectionCheck

__all__ = ["MCPNotificationInjectionCheck"]
