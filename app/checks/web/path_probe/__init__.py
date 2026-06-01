"""Re-export the entry class so `from app.checks.web.path_probe import PathProbeCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.path_probe.check import PathProbeCheck

__all__ = ["PathProbeCheck"]
