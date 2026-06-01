"""Re-export the entry class so `from app.checks.web.directory_listing import DirectoryListingCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.directory_listing.check import DirectoryListingCheck

__all__ = ["DirectoryListingCheck"]
