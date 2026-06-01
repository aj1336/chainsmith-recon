"""Re-export the entry class so `from app.checks.web.cors import CorsCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.cors.check import CorsCheck

__all__ = ["CorsCheck"]
