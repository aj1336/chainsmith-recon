"""Re-export the entry class so `from app.checks.web.sitemap import SitemapCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.sitemap.check import SitemapCheck

__all__ = ["SitemapCheck"]
