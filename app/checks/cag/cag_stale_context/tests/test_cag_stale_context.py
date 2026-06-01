"""Co-located tests (Phase 56 §3) — split from test_cag_security.py."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_stale_context import StaleContextCheck
from app.lib.http import HttpResponse


@pytest.fixture
def sample_service():
    """Sample CAG service."""
    return Service(
        url="http://cag.example.com:8080",
        host="cag.example.com",
        port=8080,
        scheme="http",
        service_type="ai",
    )


@pytest.fixture
def cag_endpoint_context(sample_service):
    """Context with CAG endpoints discovered."""
    return {
        "cag_endpoints": [
            {
                "url": "http://cag.example.com:8080/cache",
                "path": "/cache",
                "cache_type": "gptcache",
                "status_code": 200,
                "auth_required": False,
                "endpoint_type": "cache_infrastructure",
                "service": sample_service.to_dict(),
            }
        ],
        "cache_infrastructure": ["gptcache"],
    }


def make_response(
    status_code: int = 200,
    headers: dict = None,
    body: str = "",
    error: str = None,
) -> HttpResponse:
    """Create a mock HTTP response."""
    return HttpResponse(
        url="http://cag.example.com:8080/test",
        status_code=status_code,
        headers=headers or {},
        body=body,
        elapsed_ms=50.0,
        error=error,
    )


def make_mock_client(**overrides):
    """Create a standard mock HTTP client."""
    client = AsyncMock()
    client.get = AsyncMock(return_value=make_response(status_code=404))
    client.post = AsyncMock(return_value=make_response(status_code=200, body='{"answer": "ok"}'))
    client.head = AsyncMock(return_value=make_response(status_code=404))
    client._request = AsyncMock(return_value=make_response(status_code=404))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    for k, v in overrides.items():
        setattr(client, k, v)
    return client


class TestStaleContextCheck:
    @pytest.fixture
    def check(self):
        return StaleContextCheck()

    @pytest.mark.asyncio
    async def test_detects_stale_role_context(self, check, sample_service, cag_endpoint_context):
        """When fresh-session response contains admin keywords, stale context is flagged."""

        async def mock_post(url, **kwargs):
            # Both admin and fresh session queries return admin-ish content
            # (simulating stale cached admin context leaking into fresh session)
            return make_response(
                status_code=200,
                body=(
                    '{"response": "As an administrator, you have access to the following '
                    "management functions: user provisioning, system configure, audit logs, "
                    'and elevated security settings.", "context": "enterprise"}'
                ),
            )

        # Timing for _test_ttl_staleness: first request slow, second fast (caching), third fast (still cached)
        original_time = time.time
        time_values = [
            # _test_role_context: resp_admin, then asyncio.sleep, then resp_fresh
            200.0,  # various time.time calls
            200.5,
            201.0,
            201.5,
            # _test_ttl_staleness: first request
            202.0,
            202.5,  # 500ms (uncached)
            # second request
            203.0,
            203.05,  # 50ms (cached) -> 50 < 500*0.7=350 -> caching confirmed
            # post-TTL request
            204.0,
            204.05,  # 50ms (still cached -> stale)
        ]
        times = iter(time_values)

        def mock_time():
            try:
                return next(times)
            except StopIteration:
                return original_time()

        client = make_mock_client(post=mock_post)
        with (
            patch("app.checks.cag.cag_stale_context.check.AsyncHttpClient", return_value=client),
            patch("app.checks.cag.cag_stale_context.check.time.time", side_effect=mock_time),
            patch("asyncio.sleep", return_value=None),
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        # role_context test should find "administrator", "management", "configure" as stale indicators
        high_obs = [o for o in result.observations if o.severity == "high"]
        assert len(high_obs) >= 1
        assert any("stale" in o.title.lower() for o in high_obs)

    @pytest.mark.asyncio
    async def test_no_stale_context_when_responses_differ(
        self, check, sample_service, cag_endpoint_context
    ):
        """When fresh-session response has no admin content, no stale context detected."""
        call_count = 0

        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            body = kwargs.get("json", {})
            query = body.get("input", "")

            if "admin" in query.lower() or "administrator" in query.lower():
                return make_response(
                    status_code=200,
                    body='{"response": "Here are the available functions for your role."}',
                )
            # Fresh session gets completely different, non-admin content
            return make_response(
                status_code=200,
                body=f'{{"response": "Welcome, standard user. You can view reports and submit tickets.", "call": {call_count}}}',
            )

        # Timing: no caching detected for TTL test
        original_time = time.time
        time_values = []
        t = 200.0
        for _ in range(20):
            time_values.append(t)
            t += 0.5
        times = iter(time_values)

        def mock_time():
            try:
                return next(times)
            except StopIteration:
                return original_time()

        client = make_mock_client(post=mock_post)
        with (
            patch("app.checks.cag.cag_stale_context.check.AsyncHttpClient", return_value=client),
            patch("app.checks.cag.cag_stale_context.check.time.time", side_effect=mock_time),
            patch("asyncio.sleep", return_value=None),
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        # No high/critical observations expected
        high_or_crit = [o for o in result.observations if o.severity in ("high", "critical")]
        assert len(high_or_crit) == 0

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0
