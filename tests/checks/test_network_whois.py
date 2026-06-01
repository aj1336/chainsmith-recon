class TestWhoisCheckResolver:
    """Test that WhoisLookupCheck is registered in check_resolver."""

    def test_whois_lookup_registered(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "whois_lookup" in names

    def test_whois_in_network_suite(self):
        from app.check_resolver import infer_suite

        assert infer_suite("whois_lookup") == "network"

    def test_total_check_count(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        # Was 43 checks (Phase 7c), now +3 = 46
        assert len(checks) >= 46
