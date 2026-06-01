def _hop(ttl, ip=None, hostname=None, rtt_ms=None):
    """Build a hop-info dict matching _probe_hop's return shape."""
    return {"hop": ttl, "ip": ip, "hostname": hostname, "rtt_ms": rtt_ms}


class TestTracerouteCheckResolver:
    """Test that TracerouteCheck is registered in check_resolver."""

    def test_traceroute_registered(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "traceroute" in names

    def test_traceroute_in_network_suite(self):
        from app.check_resolver import infer_suite

        assert infer_suite("traceroute") == "network"
