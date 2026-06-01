"""Re-export the entry class so `from app.checks.cag.cag_injection_persistence import InjectionPersistenceCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_injection_persistence.check import InjectionPersistenceCheck

__all__ = ["InjectionPersistenceCheck"]
