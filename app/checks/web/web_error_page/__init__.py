"""Re-export the entry class so `from app.checks.web.web_error_page import ErrorPageCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_error_page.check import ErrorPageCheck

__all__ = ["ErrorPageCheck"]
