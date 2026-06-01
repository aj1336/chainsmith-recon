"""Co-located tests (Phase 56 §3) — split from test_cag_enhanced.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_cache_eviction import CacheEvictionCheck
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


class TestCacheEvictionCheck:
    @pytest.fixture
    def check(self):
        return CacheEvictionCheck()

    @pytest.mark.asyncio
    async def test_detects_accessible_clear_endpoint(
        self, check, sample_service, cag_endpoint_context
    ):
        async def mock_post(url, **kwargs):
            if "/cache/clear" in url:
                return make_response(status_code=200, body='{"status": "cleared"}')
            return make_response(status_code=404)

        client = make_mock_client(post=mock_post)
        with patch("app.checks.cag.cag_cache_eviction.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        eviction = result.outputs.get("eviction_capability", [])
        assert len(eviction) == 1
        assert eviction[0]["accessible"] is True
        assert eviction[0]["action"] == "clear"
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert obs.title == "Cache eviction endpoint: POST /cache/clear"
        assert obs.severity == "critical"

    @pytest.mark.asyncio
    async def test_detects_auth_required(self, check, sample_service, cag_endpoint_context):
        async def mock_post(url, **kwargs):
            if "/cache/clear" in url:
                return make_response(status_code=401)
            return make_response(status_code=404)

        client = make_mock_client(post=mock_post)
        with patch("app.checks.cag.cag_cache_eviction.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        auth_observations = [f for f in result.observations if f.severity == "medium"]
        assert len(auth_observations) == 1
        assert auth_observations[0].title == "Cache eviction endpoint: POST /cache/clear"

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0

    @pytest.mark.asyncio
    async def test_all_404_produces_no_observations(
        self, check, sample_service, cag_endpoint_context
    ):
        """All eviction endpoints return 404 -- nothing to report."""
        client = make_mock_client(
            post=AsyncMock(return_value=make_response(status_code=404)),
            _request=AsyncMock(return_value=make_response(status_code=404)),
        )
        with patch("app.checks.cag.cag_cache_eviction.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 0
        assert result.outputs.get("eviction_capability") is None
