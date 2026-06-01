"""Re-export the entry class so `from app.checks.cag.cag_serialization import SerializationCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_serialization.check import SerializationCheck

__all__ = ["SerializationCheck"]
