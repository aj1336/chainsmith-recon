"""Re-export the entry class so `from app.checks.web.web_default_creds import DefaultCredsCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_default_creds.check import DefaultCredsCheck

__all__ = ["DefaultCredsCheck"]
