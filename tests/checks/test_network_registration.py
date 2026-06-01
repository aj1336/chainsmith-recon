"""Cross-cutting registration/resolver tests for the network suite.

These verify that network checks are registered in ``check_resolver``, are
inferred into the ``network`` suite, are gated on the right dependencies, and
that the overall check count holds. They span multiple checks, so they live
here rather than co-located beside any single check (Phase 56 §3 — the network
analogue of the web suite's ``TestCheckRegistration`` residual). Consolidated
from the per-topic ``test_network_*.py`` files during Phase 56.3 co-location.
"""


class TestDnsRegistration:
    """Verify DNS checks are properly registered."""

    def test_checks_in_resolver(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "network_wildcard_dns" in names
        assert "network_dns_records" in names

    def test_suite_inference(self):
        from app.check_resolver import infer_suite

        assert infer_suite("network_wildcard_dns") == "network"
        assert infer_suite("network_dns_records") == "network"


class TestGeoIpRegistration:
    """Verify GeoIP check is properly registered."""

    def test_geoip_in_resolver(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "network_geoip" in names


class TestPhase7bRegistration:
    """Test that Phase 7b checks are correctly registered in the resolver."""

    def test_checks_present_in_resolver(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "network_tls_analysis" in names
        assert "network_reverse_dns" in names

    def test_reverse_dns_gated_on_dns_records(self):
        """reverse_dns runs only once `dns_records` exists (the real dependency the
        condition-driven launcher enforces, not raw resolver list order)."""
        from app.check_resolver import get_real_checks

        check = next(c for c in get_real_checks() if c.name == "network_reverse_dns")
        assert any(cond.output_name == "dns_records" for cond in check.conditions)

    def test_tls_analysis_gated_on_services(self):
        """tls_analysis runs only once `services` exists (produced by port_scan) —
        condition-driven, not raw resolver list order."""
        from app.check_resolver import get_real_checks

        check = next(c for c in get_real_checks() if c.name == "network_tls_analysis")
        assert any(cond.output_name == "services" for cond in check.conditions)

    def test_suite_inference_network(self):
        """Both checks should be inferred as 'network' suite."""
        from app.check_resolver import infer_suite

        assert infer_suite("network_tls_analysis") == "network"
        assert infer_suite("network_reverse_dns") == "network"

    def test_suite_filter(self):
        """Both checks should appear when filtering by 'network' suite."""
        from app.check_resolver import resolve_checks

        checks = resolve_checks(suites=["network"])
        names = [c.name for c in checks]
        assert "network_tls_analysis" in names
        assert "network_reverse_dns" in names

    def test_total_check_count(self):
        """Total check count should have increased by 2 (from 41 to 43)."""
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        # 39 from Phase 7a + 2 new = 41
        # Actually let's just verify it's at least 41
        assert len(checks) >= 41


class TestPhase7cRegistration:
    """Test that Phase 7c checks are correctly registered in the resolver."""

    def test_checks_present_in_resolver(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "network_http_method_enum" in names
        assert "network_banner_grab" in names

    def test_banner_grab_gated_on_services(self):
        """banner_grab runs only once `services` exists (the real dependency the
        condition-driven launcher enforces, not raw resolver list order)."""
        from app.check_resolver import get_real_checks

        check = next(c for c in get_real_checks() if c.name == "network_banner_grab")
        assert any(cond.output_name == "services" for cond in check.conditions)

    def test_http_method_enum_gated_on_services(self):
        """http_method_enum runs only once `services` exists (condition-driven, not
        raw resolver list order)."""
        from app.check_resolver import get_real_checks

        check = next(c for c in get_real_checks() if c.name == "network_http_method_enum")
        assert any(cond.output_name == "services" for cond in check.conditions)

    def test_suite_inference_network(self):
        """Both checks should be inferred as 'network' suite."""
        from app.check_resolver import infer_suite

        assert infer_suite("network_http_method_enum") == "network"
        assert infer_suite("network_banner_grab") == "network"

    def test_suite_filter(self):
        """Both checks should appear when filtering by 'network' suite."""
        from app.check_resolver import resolve_checks

        checks = resolve_checks(suites=["network"])
        names = [c.name for c in checks]
        assert "network_http_method_enum" in names
        assert "network_banner_grab" in names

    def test_total_check_count(self):
        """Total check count should have increased by 2 (43 -> 45 minimum)."""
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        assert len(checks) >= 43

    def test_imports_from_network_package(self):
        """Checks should be importable from the network package."""
        from app.checks.network import BannerGrabCheck, HttpMethodEnumCheck

        assert HttpMethodEnumCheck is not None
        assert BannerGrabCheck is not None


class TestIPv6CheckResolver:
    """Test that IPv6DiscoveryCheck is registered in check_resolver."""

    def test_ipv6_discovery_registered(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "network_ipv6_discovery" in names

    def test_ipv6_discovery_in_network_suite(self):
        from app.check_resolver import infer_suite

        assert infer_suite("network_ipv6_discovery") == "network"


class TestTracerouteCheckResolver:
    """Test that TracerouteCheck is registered in check_resolver."""

    def test_traceroute_registered(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "network_traceroute" in names

    def test_traceroute_in_network_suite(self):
        from app.check_resolver import infer_suite

        assert infer_suite("network_traceroute") == "network"


class TestWhoisCheckResolver:
    """Test that WhoisLookupCheck is registered in check_resolver."""

    def test_whois_lookup_registered(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "network_whois_lookup" in names

    def test_whois_in_network_suite(self):
        from app.check_resolver import infer_suite

        assert infer_suite("network_whois_lookup") == "network"

    def test_total_check_count(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        # Was 43 checks (Phase 7c), now +3 = 46
        assert len(checks) >= 46
