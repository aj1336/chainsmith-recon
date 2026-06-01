"""Re-export the entry class so `from app.checks.network.network_port_scan import PortScanCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.network.network_port_scan.check import PortScanCheck

__all__ = ["PortScanCheck"]
