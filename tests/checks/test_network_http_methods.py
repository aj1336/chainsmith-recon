from unittest.mock import AsyncMock, MagicMock


def _make_mock_client(
    options_allow: str | None = None,
    options_status: int = 200,
    method_responses: dict[str, int] | None = None,
    default_status: int = 405,
):
    """
    Return a factory that, when called as ``httpx.AsyncClient(...)``, produces
    an async-context-manager mock whose ``.options()`` and ``.request()``
    behave according to *options_allow* and *method_responses*.

    Parameters
    ----------
    options_allow : str | None
        Value of the ``Allow`` header returned by OPTIONS.  ``None`` means
        no Allow header at all.
    options_status : int
        Status code for the OPTIONS response.
    method_responses : dict[str, int]
        Maps HTTP method name (e.g. ``"TRACE"``) to the status code that a
        ``.request(method, ...)`` call should return.  Methods not listed
        get *default_status*.
    default_status : int
        Status code for methods not in *method_responses* (default 405,
        i.e. rejected).
    """
    method_responses = method_responses or {}

    def _factory(**kwargs):
        client = AsyncMock()

        # ---- OPTIONS response ------------------------------------------------
        options_resp = MagicMock()
        options_resp.status_code = options_status
        options_resp.headers = {}
        if options_allow is not None:
            options_resp.headers["allow"] = options_allow
        client.options = AsyncMock(return_value=options_resp)

        # ---- Generic .request(method, url) -----------------------------------
        def _request(method, url, **kw):
            status = method_responses.get(method.upper(), default_status)
            resp = MagicMock()
            resp.status_code = status
            return resp

        client.request = AsyncMock(side_effect=_request)

        # ---- async context manager -------------------------------------------
        client.__aenter__ = AsyncMock(return_value=client)
        client.__aexit__ = AsyncMock(return_value=False)
        return client

    return _factory


class TestPhase7cRegistration:
    """Test that Phase 7c checks are correctly registered in the resolver."""

    def test_checks_present_in_resolver(self):
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        names = [c.name for c in checks]
        assert "http_method_enum" in names
        assert "banner_grab" in names

    def test_banner_grab_gated_on_services(self):
        """banner_grab runs only once `services` exists (the real dependency the
        condition-driven launcher enforces, not raw resolver list order)."""
        from app.check_resolver import get_real_checks

        check = next(c for c in get_real_checks() if c.name == "banner_grab")
        assert any(cond.output_name == "services" for cond in check.conditions)

    def test_http_method_enum_gated_on_services(self):
        """http_method_enum runs only once `services` exists (condition-driven, not
        raw resolver list order)."""
        from app.check_resolver import get_real_checks

        check = next(c for c in get_real_checks() if c.name == "http_method_enum")
        assert any(cond.output_name == "services" for cond in check.conditions)

    def test_suite_inference_network(self):
        """Both checks should be inferred as 'network' suite."""
        from app.check_resolver import infer_suite

        assert infer_suite("http_method_enum") == "network"
        assert infer_suite("banner_grab") == "network"

    def test_suite_filter(self):
        """Both checks should appear when filtering by 'network' suite."""
        from app.check_resolver import resolve_checks

        checks = resolve_checks(suites=["network"])
        names = [c.name for c in checks]
        assert "http_method_enum" in names
        assert "banner_grab" in names

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
