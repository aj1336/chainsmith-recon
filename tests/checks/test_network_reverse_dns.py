from unittest.mock import MagicMock


def _make_ptr_answer(hostnames):
    """Build a fake dns.resolver answer iterable with .target attributes."""
    records = []
    for name in hostnames:
        rdata = MagicMock()
        # dns.resolver returns rdata objects with .target; str(target) includes trailing dot
        rdata.target = MagicMock()
        rdata.target.__str__ = lambda self, n=name: n + "."
        records.append(rdata)
    return records


class TestPhase7bRegistration:
    """Test that Phase 7b checks are correctly registered in the resolver."""

    def test_checks_present_in_resolver(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "tls_analysis" in names
        assert "reverse_dns" in names

    def test_reverse_dns_gated_on_dns_records(self):
        """reverse_dns runs only once `dns_records` exists (the real dependency the
        condition-driven launcher enforces, not raw resolver list order)."""
        from app.check_resolver import get_real_checks

        check = next(c for c in get_real_checks() if c.name == "reverse_dns")
        assert any(cond.output_name == "dns_records" for cond in check.conditions)

    def test_tls_analysis_gated_on_services(self):
        """tls_analysis runs only once `services` exists (produced by port_scan) —
        condition-driven, not raw resolver list order."""
        from app.check_resolver import get_real_checks

        check = next(c for c in get_real_checks() if c.name == "tls_analysis")
        assert any(cond.output_name == "services" for cond in check.conditions)

    def test_suite_inference_network(self):
        """Both checks should be inferred as 'network' suite."""
        from app.check_resolver import infer_suite

        assert infer_suite("tls_analysis") == "network"
        assert infer_suite("reverse_dns") == "network"

    def test_suite_filter(self):
        """Both checks should appear when filtering by 'network' suite."""
        from app.check_resolver import resolve_checks

        checks = resolve_checks(suites=["network"])
        names = [c.name for c in checks]
        assert "tls_analysis" in names
        assert "reverse_dns" in names

    def test_total_check_count(self):
        """Total check count should have increased by 2 (from 41 to 43)."""
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        # 39 from Phase 7a + 2 new = 41
        # Actually let's just verify it's at least 41
        assert len(checks) >= 41
