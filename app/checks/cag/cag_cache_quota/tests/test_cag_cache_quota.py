"""Co-located tests (Phase 56 §3) — split from test_cag_enhanced.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_cache_quota import CacheQuotaCheck
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


class TestCacheQuotaCheck:
    @pytest.fixture
    def check(self):
        return CacheQuotaCheck()

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0

    @pytest.mark.asyncio
    async def test_detects_eviction(self, check, sample_service, cag_endpoint_context):
        """When early entries are evicted, reports cache exhaustion."""
        quota_info = {
            "url": "http://cag.example.com:8080/cache",
            "total_entries_sent": 50,
            "early_entries_evicted": 3,
            "early_entries_checked": 5,
            "last_entries_cached": 3,
            "baseline_ms": 200.0,
            "cached_ms": 30.0,
            "eviction_detected": True,
            "unbounded": False,
            "estimated_capacity": 47,
        }
        with patch.object(check, "_test_quota", return_value=quota_info):
            client = make_mock_client()
            with patch("app.checks.cag.cag_cache_quota.check.AsyncHttpClient", return_value=client):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert "Cache exhaustion possible" in obs.title
        assert "3 early entries evicted" in obs.title
        assert obs.severity == "medium"
        assert result.outputs["cache_size"] == [quota_info]

    @pytest.mark.asyncio
    async def test_detects_unbounded_cache(self, check, sample_service, cag_endpoint_context):
        """When no eviction occurs, reports unbounded cache risk."""
        quota_info = {
            "url": "http://cag.example.com:8080/cache",
            "total_entries_sent": 50,
            "early_entries_evicted": 0,
            "early_entries_checked": 5,
            "last_entries_cached": 3,
            "baseline_ms": 200.0,
            "cached_ms": 30.0,
            "eviction_detected": False,
            "unbounded": True,
            "estimated_capacity": 50,
        }
        with patch.object(check, "_test_quota", return_value=quota_info):
            client = make_mock_client()
            with patch("app.checks.cag.cag_cache_quota.check.AsyncHttpClient", return_value=client):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert "Unbounded cache" in obs.title
        assert "memory exhaustion risk" in obs.title
        assert obs.severity == "medium"

    @pytest.mark.asyncio
    async def test_no_caching_detected_produces_no_observations(
        self, check, sample_service, cag_endpoint_context
    ):
        """When _test_quota returns None (no caching), no observations."""
        with patch.object(check, "_test_quota", return_value=None):
            client = make_mock_client()
            with patch("app.checks.cag.cag_cache_quota.check.AsyncHttpClient", return_value=client):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 0
        assert "cache_size" not in result.outputs
