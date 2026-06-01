"""Re-export the entry class so `from app.checks.web.web_mass_assignment import MassAssignmentCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_mass_assignment.check import MassAssignmentCheck

__all__ = ["MassAssignmentCheck"]
