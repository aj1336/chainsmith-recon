def _resolver_side_effect(records: dict):
    """Return a side_effect callable for mock resolver.resolve().

    Args:
        records: mapping of record type (e.g. "MX") to list of mock rdata objects.
            Unlisted types raise NoAnswer.
    """
    import dns.resolver as _dns_resolver

    def _resolve(domain, rtype):
        if rtype in records:
            return records[rtype]
        raise _dns_resolver.NoAnswer()

    return _resolve


class TestDnsRegistration:
    """Verify DNS checks are properly registered."""

    def test_checks_in_resolver(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "wildcard_dns" in names
        assert "dns_records" in names

    def test_suite_inference(self):
        from app.check_resolver import infer_suite

        assert infer_suite("wildcard_dns") == "network"
        assert infer_suite("dns_records") == "network"
