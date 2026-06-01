"""Co-located tests (Phase 56 §3) — split from test_cag_enhanced.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_multi_layer_cache import MultiLayerCacheCheck
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


class TestMultiLayerCacheCheck:
    @pytest.fixture
    def check(self):
        return MultiLayerCacheCheck()

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0

    @pytest.mark.asyncio
    async def test_detects_multiple_layers(self, check, sample_service, cag_endpoint_context):
        """When multiple cache layers are detected, observation reflects that."""
        layer_info = {
            "url": "http://cag.example.com:8080/cache",
            "timings": {
                "normal": {
                    "elapsed_ms": 20.0,
                    "status_code": 200,
                    "cache_headers": {},
                    "response_length": 100,
                },
                "no_cache": {
                    "elapsed_ms": 50.0,
                    "status_code": 200,
                    "cache_headers": {},
                    "response_length": 100,
                },
                "pragma": {
                    "elapsed_ms": 45.0,
                    "status_code": 200,
                    "cache_headers": {},
                    "response_length": 100,
                },
                "cache_buster": {
                    "elapsed_ms": 200.0,
                    "status_code": 200,
                    "cache_headers": {},
                    "response_length": 100,
                },
            },
            "layers_detected": 2,
            "layers": [
                {
                    "type": "http_cache",
                    "bypass_method": "Cache-Control: no-cache",
                    "normal_ms": 20.0,
                    "bypassed_ms": 50.0,
                },
                {
                    "type": "application_cache",
                    "bypass_method": "none (ignores HTTP cache headers)",
                    "normal_ms": 50.0,
                    "bypassed_ms": 200.0,
                },
            ],
        }
        with patch.object(check, "_detect_layers", return_value=layer_info):
            client = make_mock_client()
            with patch(
                "app.checks.cag.cag_multi_layer_cache.check.AsyncHttpClient", return_value=client
            ):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert (
            obs.title == "Multiple cache layers detected: 2 layers with different bypass behavior"
        )
        assert obs.severity == "medium"
        assert result.outputs["cache_layers"] == [layer_info]

    @pytest.mark.asyncio
    async def test_detects_single_semantic_layer(self, check, sample_service, cag_endpoint_context):
        """Single semantic cache layer produces info severity."""
        layer_info = {
            "url": "http://cag.example.com:8080/cache",
            "timings": {
                "normal": {
                    "elapsed_ms": 20.0,
                    "status_code": 200,
                    "cache_headers": {},
                    "response_length": 100,
                },
                "no_cache": {
                    "elapsed_ms": 22.0,
                    "status_code": 200,
                    "cache_headers": {},
                    "response_length": 100,
                },
                "pragma": {
                    "elapsed_ms": 21.0,
                    "status_code": 200,
                    "cache_headers": {},
                    "response_length": 100,
                },
                "cache_buster": {
                    "elapsed_ms": 23.0,
                    "status_code": 200,
                    "cache_headers": {},
                    "response_length": 100,
                },
            },
            "layers_detected": 1,
            "layers": [
                {
                    "type": "semantic_or_application_cache",
                    "bypass_method": "none detected",
                    "note": "Cache ignores all HTTP cache-busting strategies",
                },
            ],
        }
        with patch.object(check, "_detect_layers", return_value=layer_info):
            client = make_mock_client()
            with patch(
                "app.checks.cag.cag_multi_layer_cache.check.AsyncHttpClient", return_value=client
            ):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert obs.title == "Single cache layer detected (semantic_or_application_cache)"
        assert obs.severity == "info"

    @pytest.mark.asyncio
    async def test_no_layers_detected_produces_no_observations(
        self, check, sample_service, cag_endpoint_context
    ):
        """When _detect_layers returns None, no observations."""
        with patch.object(check, "_detect_layers", return_value=None):
            client = make_mock_client()
            with patch(
                "app.checks.cag.cag_multi_layer_cache.check.AsyncHttpClient", return_value=client
            ):
                result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 0
        assert "cache_layers" not in result.outputs
