"""Cross-cutting registration tests for the agent suite."""


class TestRegistration:
    def test_get_checks_returns_all_exported_classes(self):
        """get_checks() should return every class listed in __all__."""
        from app.checks.agent import __all__ as exported_names
        from app.checks.agent import get_checks

        checks = get_checks()
        check_class_names = {cls.__name__ for cls in checks}
        assert check_class_names == set(exported_names)

    def test_all_checks_have_unique_names(self):
        from app.checks.agent import get_checks

        checks = get_checks()
        names = [cls().name for cls in checks]
        assert len(names) == len(set(names)), f"Duplicate check names: {names}"

    def test_check_resolver_includes_agent_checks(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        agent_checks = [c for c in checks if "agent" in c.name]
        # At least the two checks tested in this file should be present
        agent_names = {c.name for c in agent_checks}
        assert "agent_trust_chain" in agent_names
        assert "agent_cross_injection" in agent_names
