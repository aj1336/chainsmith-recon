"""Cross-cutting registration test for the web suite.

Verifies that the web checks are registered in ``check_resolver`` and inferred
into the ``web`` suite. This spans multiple checks, so it lives here rather than
co-located beside any single check (Phase 56 §3 — the web analogue of the
network suite's ``test_network_registration.py``). Extracted from the former
``test_web_default_debug.py`` residual during Phase 56 co-location cleanup.
"""


class TestCheckRegistration:
    def test_all_checks_registered(self):
        from app.check_resolver import get_real_checks, infer_suite

        checks = get_real_checks()
        web_checks = [c for c in checks if infer_suite(c.name) == "web"]
        web_names = {c.name for c in web_checks}

        expected = {
            "web_webdav",
            "web_vcs_exposure",
            "web_config_exposure",
            "web_directory_listing",
            "web_default_creds",
            "web_debug_endpoints",
        }
        assert expected.issubset(web_names), f"Missing: {expected - web_names}"
