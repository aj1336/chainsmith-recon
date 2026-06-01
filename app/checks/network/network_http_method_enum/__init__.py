"""Re-export the entry class so `from app.checks.network.network_http_method_enum import HttpMethodEnumCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.network_http_method_enum.check import HttpMethodEnumCheck

__all__ = ["HttpMethodEnumCheck"]
