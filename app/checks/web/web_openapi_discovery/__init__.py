"""Re-export the entry class so `from app.checks.web.web_openapi_discovery import OpenAPICheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_openapi_discovery.check import OpenAPICheck

__all__ = ["OpenAPICheck"]
