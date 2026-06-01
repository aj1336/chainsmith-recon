"""Co-located tests (Phase 56 §3) — split from test_cag_security.py."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_semantic_threshold import SemanticThresholdCheck
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


class TestSemanticThresholdCheck:
    @pytest.fixture
    def check(self):
        return SemanticThresholdCheck()

    @pytest.mark.asyncio
    async def test_detects_loose_semantic_threshold(
        self, check, sample_service, cag_endpoint_context
    ):
        """When many rephrased/related queries produce cache hits, a loose threshold is flagged."""
        baseline_body = (
            '{"response": "The capital of France is Paris, a city known for the Eiffel Tower."}'
        )

        async def mock_post(url, **kwargs):
            return make_response(status_code=200, body=baseline_body)

        # Control timing: cold=500ms, hot=50ms, all variations=50ms (all cache hits)
        original_time = time.time
        times = iter(
            [
                # cold request
                100.0,
                100.5,  # 500ms
                # hot request (confirm caching)
                101.0,
                101.05,  # 50ms < 500*0.7=350ms -> caching confirmed
                # threshold = 500 * 0.7 = 350ms
                # 5 variation probes (all fast -> cache hit)
                102.0,
                102.05,  # minor_variation: 50ms
                103.0,
                103.05,  # rephrased: 50ms
                104.0,
                104.05,  # related: 50ms
                105.0,
                105.05,  # tangential: 50ms
                106.0,
                106.05,  # unrelated: 50ms
            ]
        )

        def mock_time():
            try:
                return next(times)
            except StopIteration:
                return original_time()

        client = make_mock_client(post=mock_post)
        with (
            patch(
                "app.checks.cag.cag_semantic_threshold.check.AsyncHttpClient", return_value=client
            ),
            patch("app.checks.cag.cag_semantic_threshold.check.time.time", side_effect=mock_time),
            patch("asyncio.sleep", return_value=None),
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) >= 1
        # 5 hits with rephrased/related/tangential -> is_semantic=True, hits>=4 -> high
        obs = result.observations[0]
        assert obs.severity in ("high", "medium")
        assert "semantic" in obs.title.lower() or "threshold" in obs.title.lower()

    @pytest.mark.asyncio
    async def test_exact_match_only_reports_info(self, check, sample_service, cag_endpoint_context):
        """When no variations hit the cache, it's not a semantic cache -> info."""
        call_count = 0

        async def mock_post(url, **kwargs):
            nonlocal call_count
            call_count += 1
            return make_response(
                status_code=200,
                body=f'{{"response": "answer-{call_count}", "id": {call_count}}}',
            )

        # cold=500ms, hot=50ms (caching works), all variants=600ms (all miss)
        original_time = time.time
        times = iter(
            [
                100.0,
                100.5,  # cold: 500ms
                101.0,
                101.05,  # hot: 50ms -> caching confirmed
                # 5 variations - all slow (cache miss)
                102.0,
                102.6,  # 600ms > 350ms
                103.0,
                103.6,
                104.0,
                104.6,
                105.0,
                105.6,
                106.0,
                106.6,
            ]
        )

        def mock_time():
            try:
                return next(times)
            except StopIteration:
                return original_time()

        client = make_mock_client(post=mock_post)
        with (
            patch(
                "app.checks.cag.cag_semantic_threshold.check.AsyncHttpClient", return_value=client
            ),
            patch("app.checks.cag.cag_semantic_threshold.check.time.time", side_effect=mock_time),
            patch("asyncio.sleep", return_value=None),
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) >= 1
        obs = result.observations[0]
        assert obs.severity == "info"
        assert "not a semantic cache" in obs.title.lower() or "exact match" in obs.title.lower()

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0
