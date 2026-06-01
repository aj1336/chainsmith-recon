"""Re-export the entry class so `from app.checks.web.web_cookie_security import CookieSecurityCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_cookie_security.check import CookieSecurityCheck

__all__ = ["CookieSecurityCheck"]
