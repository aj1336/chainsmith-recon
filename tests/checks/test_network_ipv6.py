class TestIPv6CheckResolver:
    """Test that IPv6DiscoveryCheck is registered in check_resolver."""

    def test_ipv6_discovery_registered(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "ipv6_discovery" in names

    def test_ipv6_discovery_in_network_suite(self):
        from app.check_resolver import infer_suite

        assert infer_suite("ipv6_discovery") == "network"
