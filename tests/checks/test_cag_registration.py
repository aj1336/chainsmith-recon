"""Cross-cutting registration tests for the cag suite."""


class TestCAGRegistry:
    def test_all_checks_registered(self):
        from app.checks.cag import get_checks

        checks = get_checks()
        # Verify known checks are present without hardcoding a count
        assert len(checks) >= 10, "Expected at least 10 CAG checks registered"

        names = [cls().name for cls in checks]
        # Verify key checks from each phase are present
        for expected in [
            "cag_discovery",
            "cag_cache_probe",
            "cag_cross_user_leakage",
            "cag_cache_poisoning",
            "cag_serialization",
            "cag_distributed_cache",
        ]:
            assert expected in names, f"Expected {expected} in registry"

    def test_all_checks_have_produces(self):
        from app.checks.cag import get_checks

        for cls in get_checks():
            check = cls()
            assert len(check.produces) > 0, f"{check.name} has no produces"

    def test_all_checks_have_conditions(self):
        from app.checks.cag import get_checks

        for cls in get_checks():
            check = cls()
            assert len(check.conditions) > 0, f"{check.name} has no conditions"
