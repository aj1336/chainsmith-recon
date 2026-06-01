"""Co-located tests (Phase 56 §3) — split from test_cag_security.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_cross_user_leakage import CrossUserLeakageCheck
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


class TestCrossUserLeakageCheck:
    @pytest.fixture
    def check(self):
        return CrossUserLeakageCheck()

    @pytest.mark.asyncio
    async def test_detects_auth_leakage(self, check, sample_service, cag_endpoint_context):
        """Auth response served without auth = critical leakage.

        The check compares bodies from auth vs no-auth requests. When
        both are identical and > 50 chars, leakage is flagged.
        """
        # Realistic cached LLM response that happens to be > 50 chars and identical
        # regardless of whether auth headers are present (simulating no cache-key
        # differentiation on auth state).
        shared_body = (
            '{"response": "Based on the quarterly financial report, the projected '
            "revenue for Q3 is estimated at $4.2M with a 12% growth rate over the "
            'previous quarter. The board has approved the expansion plan.", '
            '"model": "gpt-4", "cached": true}'
        )

        async def mock_post(url, **kwargs):
            return make_response(status_code=200, body=shared_body)

        client = make_mock_client(post=mock_post)
        with patch(
            "app.checks.cag.cag_cross_user_leakage.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        critical_obs = [o for o in result.observations if o.severity == "critical"]
        assert len(critical_obs) >= 1
        assert "auth response served without auth" in critical_obs[0].title.lower()

    @pytest.mark.asyncio
    async def test_no_leakage_detected(self, check, sample_service, cag_endpoint_context):
        """Different responses per auth context = proper isolation."""
        call_count = 0

        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            # Each call returns a distinct response body that differs enough
            return make_response(
                status_code=200,
                body=f'{{"response": "Unique answer #{call_count} generated at request time", '
                f'"request_id": "req-{call_count:04d}", "cached": false}}',
            )

        client = make_mock_client(post=mock_post)
        with patch(
            "app.checks.cag.cag_cross_user_leakage.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        info_obs = [o for o in result.observations if o.severity == "info"]
        assert len(info_obs) >= 1
        assert "properly isolates" in info_obs[0].title.lower()

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0
