"""Re-export the entry class so `from app.checks.web.redirect_chain import RedirectChainCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.redirect_chain.check import RedirectChainCheck

__all__ = ["RedirectChainCheck"]
