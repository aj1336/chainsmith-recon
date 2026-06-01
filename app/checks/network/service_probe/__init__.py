"""Re-export the entry class so `from app.checks.network.service_probe import ServiceProbeCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.service_probe.check import ServiceProbeCheck

__all__ = ["ServiceProbeCheck"]
