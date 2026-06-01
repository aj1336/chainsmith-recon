"""Co-located tests (Phase 56 §3) — split from test_cag_security.py."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_side_channel import SideChannelCheck
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


class TestSideChannelCheck:
    @pytest.fixture
    def check(self):
        return SideChannelCheck()

    @pytest.mark.asyncio
    async def test_detects_timing_side_channel(self, check, sample_service, cag_endpoint_context):
        """When sensitive topic queries are faster than baseline, cache hits indicate side channel."""
        call_index = 0

        async def mock_post(url, **kwargs):
            nonlocal call_index
            call_index += 1
            # All queries return a realistic LLM-style answer
            return make_response(
                status_code=200,
                body=f'{{"response": "Here is some information about your query.", "req": {call_index}}}',
            )

        # Timing: baseline queries ~500ms each (3 calls), then sensitive topic queries
        # Each topic is queried 3 times. We want some topics to be fast (cache hit).
        # baseline: 3 unique queries at ~500ms each
        # Then 8 topics x 3 requests each = 24 requests
        # Make all topic requests fast (50ms) to simulate cache hits
        original_time = time.time
        time_values = []
        t = 100.0
        # 3 baseline queries: ~500ms each
        for _ in range(3):
            time_values.append(t)
            t += 0.5  # 500ms
            time_values.append(t)
            t += 0.1
        # 8 topics x 3 requests each: ~50ms each (cache hit)
        for _ in range(24):
            time_values.append(t)
            t += 0.02  # 20ms << 250ms threshold (500*0.5)
            time_values.append(t)
            t += 0.01
        # Also need stddev to be low for cache hit detection
        times = iter(time_values)

        def mock_time():
            try:
                return next(times)
            except StopIteration:
                return original_time()

        client = make_mock_client(post=mock_post)
        with (
            patch("app.checks.cag.cag_side_channel.check.AsyncHttpClient", return_value=client),
            patch("app.checks.cag.cag_side_channel.check.time.time", side_effect=mock_time),
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) >= 1
        obs = result.observations[0]
        assert obs.severity in ("medium", "low")
        assert "side-channel" in obs.title.lower() or "timing" in obs.title.lower()

    @pytest.mark.asyncio
    async def test_no_side_channel_when_endpoint_errors(
        self, check, sample_service, cag_endpoint_context
    ):
        """When all baseline requests error, no side channel analysis is possible."""

        async def mock_post(url, **kwargs):
            return make_response(status_code=500, body='{"error": "server error"}', error="500")

        client = make_mock_client(post=mock_post)
        with patch("app.checks.cag.cag_side_channel.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        # No observations when baseline fails
        assert len(result.observations) == 0

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0
