"""Co-located tests (Phase 56 §3) — split from test_cag_security.py."""

import time
from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_cache_key_reverse import CacheKeyReverseCheck
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


class TestCacheKeyReverseCheck:
    @pytest.fixture
    def check(self):
        return CacheKeyReverseCheck()

    @pytest.mark.asyncio
    async def test_detects_case_insensitive_key(self, check, sample_service, cag_endpoint_context):
        """When variant queries return fast (cache hit), the component is NOT in the key.

        The check first establishes baseline timing. If the second (identical) request
        is faster than 70% of the first, caching is detected. Then it sends KEY_COMPONENT_TESTS
        variants; if the variant is fast, the component is excluded from the key.
        """
        request_count = 0

        async def mock_post(url, **kwargs):
            nonlocal request_count
            request_count += 1
            body = kwargs.get("json", {})
            query = body.get("input", "")

            # Baseline timing probe: first request slow, second fast
            if "baseline_key_test_" in query:
                if request_count <= 1:
                    # Uncached - simulate by returning after some body
                    return make_response(
                        status_code=200,
                        body='{"answer": "The capital of France is Paris.", "latency": "cold"}',
                    )
                else:
                    # Cached - same response
                    return make_response(
                        status_code=200,
                        body='{"answer": "The capital of France is Paris.", "latency": "warm"}',
                    )

            # All key component tests - return fast (cache hit) to simulate
            # key ignoring that component
            return make_response(
                status_code=200,
                body='{"answer": "The capital of France is Paris.", "cached": true}',
            )

        # Patch time.time to control timing analysis
        # _get_baseline_timing:
        #   1 call for query string: time.time() in f-string
        #   2 calls for uncached request: start1, end1
        #   2 calls for cached request: start2, end2
        # _test_key_component: 2 calls each (start, end) x 5 tests = 10
        # _test_system_prompt_key: 2 calls (start, end)
        # Total: 5 + 10 + 2 = 17 time.time() calls
        original_time = time.time
        call_times = iter(
            [
                # _get_baseline_timing:
                100.0,  # query string timestamp (ignored for timing)
                100.1,  # start1 (uncached request)
                100.6,  # end1 -> uncached_ms = 500ms
                101.0,  # start2 (cached request)
                101.1,  # end2 -> cached_ms = 100ms < 500*0.7=350ms -> caching detected
                # cache_hit_threshold = 500 * 0.7 = 350ms
                # _test_key_component: capitalization (variant fast -> cache hit -> NOT in key)
                103.0,  # start variant
                103.1,  # end variant (100ms < 350ms)
                # _test_key_component: punctuation
                105.0,
                105.1,  # 100ms -> cache hit
                # _test_key_component: whitespace
                107.0,
                107.1,  # 100ms -> cache hit
                # _test_key_component: prefix
                109.0,
                109.1,  # 100ms -> cache hit
                # _test_key_component: suffix
                111.0,
                111.1,  # 100ms -> cache hit
                # _test_system_prompt_key: system_prompt
                113.0,
                113.1,  # 100ms -> cache hit -> system prompt NOT in key
            ]
        )

        def mock_time():
            try:
                return next(call_times)
            except StopIteration:
                return original_time()

        client = make_mock_client(post=mock_post)
        with (
            patch(
                "app.checks.cag.cag_cache_key_reverse.check.AsyncHttpClient", return_value=client
            ),
            patch("app.checks.cag.cag_cache_key_reverse.check.time.time", side_effect=mock_time),
            patch("asyncio.sleep", return_value=None),
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        # Should detect system prompt exclusion (high) and case/whitespace insensitivity (medium)
        high_obs = [o for o in result.observations if o.severity == "high"]
        assert len(high_obs) >= 1
        assert "system prompt" in high_obs[0].title.lower()

        medium_obs = [o for o in result.observations if o.severity == "medium"]
        assert len(medium_obs) >= 1

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0

    @pytest.mark.asyncio
    async def test_no_caching_detected_produces_no_observations(
        self, check, sample_service, cag_endpoint_context
    ):
        """When the endpoint doesn't cache, baseline detection fails and no observations are emitted."""

        async def mock_post(url, **kwargs):
            return make_response(
                status_code=200,
                body='{"answer": "dynamic response", "ts": "2024-01-01T00:00:00"}',
            )

        # 5 time.time calls in _get_baseline_timing: query_ts, start1, end1, start2, end2
        # Both requests take same time -> caching_detected = False
        original_time = time.time
        times = iter([100.0, 100.1, 100.6, 101.0, 101.5])

        def mock_time():
            try:
                return next(times)
            except StopIteration:
                return original_time()

        client = make_mock_client(post=mock_post)
        with (
            patch(
                "app.checks.cag.cag_cache_key_reverse.check.AsyncHttpClient", return_value=client
            ),
            patch("app.checks.cag.cag_cache_key_reverse.check.time.time", side_effect=mock_time),
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 0
