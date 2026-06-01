"""Re-export the entry class so `from app.checks.web.web_sitemap import SitemapCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_sitemap.check import SitemapCheck

__all__ = ["SitemapCheck"]
