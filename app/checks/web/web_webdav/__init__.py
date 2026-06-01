"""Re-export the entry class so `from app.checks.web.web_webdav import WebDAVCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_webdav.check import WebDAVCheck

__all__ = ["WebDAVCheck"]
