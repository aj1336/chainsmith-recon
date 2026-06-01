"""Re-export the entry class so `from app.checks.web.favicon import FaviconCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.favicon.check import FaviconCheck

__all__ = ["FaviconCheck"]
