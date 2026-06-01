"""Co-located tests (Phase 56 §3) — split from test_cag_enhanced.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_provider_caching import ProviderCachingCheck
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


class TestProviderCachingCheck:
    @pytest.fixture
    def check(self):
        return ProviderCachingCheck()

    @pytest.mark.asyncio
    async def test_detects_cached_tokens(self, check, sample_service, cag_endpoint_context):
        async def mock_post(url, **kwargs):
            return make_response(
                status_code=200,
                body='{"usage": {"cached_tokens": 150, "prompt_tokens": 300}, "choices": []}',
            )

        client = make_mock_client(post=mock_post)
        with patch(
            "app.checks.cag.cag_provider_caching.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        provider_info = result.outputs.get("provider_cache_info", [])
        assert len(provider_info) == 1
        assert provider_info[0]["caching_detected"] is True
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert obs.severity in ("low", "medium")

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0

    @pytest.mark.asyncio
    async def test_no_caching_detected(self, check, sample_service, cag_endpoint_context):
        """When provider returns no usage metadata, no observations."""

        async def mock_post(url, **kwargs):
            return make_response(status_code=200, body='{"result": "hello"}')

        client = make_mock_client(post=mock_post)
        with patch(
            "app.checks.cag.cag_provider_caching.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 0
        assert "provider_cache_info" not in result.outputs

    @pytest.mark.asyncio
    async def test_shared_prefix_detected(self, check, sample_service, cag_endpoint_context):
        """When multiple queries show similar cached token counts, shared prefix is detected."""
        cache_info = {
            "url": "http://cag.example.com:8080/cache",
            "tests_run": 3,
            "caching_detected": True,
            "shared_prefix_detected": True,
            "results": [
                {"cached_tokens": 150, "total_tokens": 300, "cache_ratio": 0.5, "test_index": 0},
                {"cached_tokens": 148, "total_tokens": 310, "cache_ratio": 0.48, "test_index": 1},
            ],
        }
        with patch.object(check, "_analyze_provider_caching", return_value=cache_info):
            client = make_mock_client()
            with patch(
                "app.checks.cag.cag_provider_caching.check.AsyncHttpClient", return_value=client
            ):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert obs.title == "Provider caching reveals shared system prompt across queries"
        assert obs.severity == "medium"
