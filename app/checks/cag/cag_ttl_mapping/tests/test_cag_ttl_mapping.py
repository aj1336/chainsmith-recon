"""Co-located tests (Phase 56 §3) — split from test_cag_enhanced.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_ttl_mapping import TTLMappingCheck
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


class TestTTLMappingCheck:
    @pytest.fixture
    def check(self):
        return TTLMappingCheck()

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0

    @pytest.mark.asyncio
    async def test_detects_unbounded_ttl(self, check, sample_service, cag_endpoint_context):
        """When _map_ttl finds no expiry, observation reports unbounded TTL."""
        ttl_info = {
            "url": "http://cag.example.com:8080/cache",
            "caching_detected": True,
            "initial_request_ms": 200.0,
            "cached_request_ms": 30.0,
            "speedup_ratio": 0.85,
            "header_ttl_seconds": None,
            "observed_ttl_seconds": None,
            "last_cache_hit_interval": 60,
            "ttl_unbounded": True,
            "ttl_mismatch": False,
        }
        with patch.object(check, "_map_ttl", return_value=ttl_info):
            client = make_mock_client()
            with patch("app.checks.cag.cag_ttl_mapping.check.AsyncHttpClient", return_value=client):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert obs.title == "Unbounded cache TTL (no expiry detected within test window)"
        assert obs.severity == "medium"
        assert result.outputs["cache_ttl"] == [ttl_info]

    @pytest.mark.asyncio
    async def test_detects_ttl_mismatch(self, check, sample_service, cag_endpoint_context):
        """When header TTL and observed TTL differ, report mismatch."""
        ttl_info = {
            "url": "http://cag.example.com:8080/cache",
            "caching_detected": True,
            "initial_request_ms": 200.0,
            "cached_request_ms": 30.0,
            "speedup_ratio": 0.85,
            "header_ttl_seconds": 60,
            "observed_ttl_seconds": 15,
            "last_cache_hit_interval": 5,
            "ttl_unbounded": False,
            "ttl_mismatch": True,
        }
        with patch.object(check, "_map_ttl", return_value=ttl_info):
            client = make_mock_client()
            with patch("app.checks.cag.cag_ttl_mapping.check.AsyncHttpClient", return_value=client):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert "mismatch" in obs.title.lower()
        assert obs.severity == "low"

    @pytest.mark.asyncio
    async def test_no_caching_detected_produces_no_observations(
        self, check, sample_service, cag_endpoint_context
    ):
        """When _map_ttl returns None (no caching), no observations."""
        with patch.object(check, "_map_ttl", return_value=None):
            client = make_mock_client()
            with patch("app.checks.cag.cag_ttl_mapping.check.AsyncHttpClient", return_value=client):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 0
        assert "cache_ttl" not in result.outputs
