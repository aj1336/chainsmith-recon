"""Re-export the entry class so `from app.checks.mcp.server_fingerprint import MCPServerFingerprintCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.mcp.server_fingerprint.check import MCPServerFingerprintCheck

__all__ = ["MCPServerFingerprintCheck"]
