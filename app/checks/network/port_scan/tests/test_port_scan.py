"""Co-located tests (Phase 56 §3) — split from test_port_profiles.py."""

from unittest.mock import MagicMock, patch

from app.checks.network.port_profiles import (
    PROFILES,
)


class TestPortScanCheckResolution:
    """Tests for PortScanCheck._resolve_ports() integration with config."""

    def _make_config(self, port_profile="lab", in_scope_ports=None):
        """Create a mock config."""
        cfg = MagicMock()
        cfg.scope.port_profile = port_profile
        cfg.scope.in_scope_ports = in_scope_ports or []
        return cfg

    @patch("app.checks.network.port_scan.check.get_config")
    def test_uses_config_profile(self, mock_get_config):
        from app.checks.network.port_scan import PortScanCheck

        mock_get_config.return_value = self._make_config(port_profile="web")

        check = PortScanCheck()
        ports = check._resolve_ports({})

        assert ports == PROFILES["web"]

    @patch("app.checks.network.port_scan.check.get_config")
    def test_context_overrides_config_profile(self, mock_get_config):
        from app.checks.network.port_scan import PortScanCheck

        mock_get_config.return_value = self._make_config(port_profile="web")

        check = PortScanCheck()
        ports = check._resolve_ports({"port_profile": "ai"})

        assert ports == PROFILES["ai"]

    @patch("app.checks.network.port_scan.check.get_config")
    def test_explicit_profile_overrides_context(self, mock_get_config):
        from app.checks.network.port_scan import PortScanCheck

        mock_get_config.return_value = self._make_config(port_profile="web")

        check = PortScanCheck(profile="full")
        ports = check._resolve_ports({"port_profile": "ai"})

        assert ports == PROFILES["full"]

    @patch("app.checks.network.port_scan.check.get_config")
    def test_explicit_ports_bypass_profile(self, mock_get_config):
        from app.checks.network.port_scan import PortScanCheck

        mock_get_config.return_value = self._make_config()

        check = PortScanCheck(ports=[22, 80, 443])
        ports = check._resolve_ports({})

        assert ports == [22, 80, 443]

    @patch("app.checks.network.port_scan.check.get_config")
    def test_in_scope_ports_filters_profile(self, mock_get_config):
        from app.checks.network.port_scan import PortScanCheck

        mock_get_config.return_value = self._make_config(
            port_profile="lab",
            in_scope_ports=[80, 443],
        )

        check = PortScanCheck()
        ports = check._resolve_ports({})

        assert ports == [80, 443]

    @patch("app.checks.network.port_scan.check.get_config")
    def test_in_scope_ports_filters_explicit_ports(self, mock_get_config):
        from app.checks.network.port_scan import PortScanCheck

        mock_get_config.return_value = self._make_config(
            in_scope_ports=[80, 443],
        )

        check = PortScanCheck(ports=[22, 80, 443, 8080])
        ports = check._resolve_ports({})

        assert 80 in ports
        assert 443 in ports
        assert 22 not in ports
        assert 8080 not in ports
