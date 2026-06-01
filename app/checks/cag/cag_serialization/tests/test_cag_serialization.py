"""Co-located tests (Phase 56 §3) — split from test_cag_security.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.cag.cag_serialization import SerializationCheck
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


class TestSerializationCheck:
    @pytest.fixture
    def check(self):
        return SerializationCheck()

    @pytest.mark.asyncio
    async def test_detects_redis_access(self, check, sample_service, cag_endpoint_context):
        """When a Redis info endpoint is reachable, an observation is raised."""

        async def mock_get(url, **kwargs):
            if "/redis" in url:
                # Realistic Redis INFO output embedded in surrounding content
                return make_response(
                    status_code=200,
                    body=(
                        "# Server\r\n"
                        "redis_version:7.0.11\r\n"
                        "redis_git_sha1:00000000\r\n"
                        "redis_build_id:abc123\r\n"
                        "os:Linux 5.15.0 x86_64\r\n"
                        "# Clients\r\n"
                        "connected_clients:42\r\n"
                        "blocked_clients:0\r\n"
                        "# Memory\r\n"
                        "used_memory:1024000\r\n"
                        "used_memory_human:1000.00K\r\n"
                    ),
                )
            return make_response(status_code=404)

        client = make_mock_client(get=mock_get)
        with patch("app.checks.cag.cag_serialization.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        redis_obs = [o for o in result.observations if "redis" in o.title.lower()]
        assert len(redis_obs) >= 1
        assert redis_obs[0].severity in ("high", "critical")
        assert "without auth" in redis_obs[0].title.lower()

    @pytest.mark.asyncio
    async def test_detects_pickle_serialization(self, check, sample_service, cag_endpoint_context):
        """When error responses mention pickle, a critical observation is raised."""

        async def mock_get(url, **kwargs):
            return make_response(status_code=404)

        async def mock_post(url, **kwargs):
            headers = kwargs.get("headers", {})
            if headers.get("Content-Type") == "application/octet-stream":
                return make_response(
                    status_code=500,
                    body=(
                        '{"error": "Failed to deserialize cache entry: '
                        "could not unpickle object from binary stream. "
                        'Ensure the data was serialized with pickle protocol 4."}'
                    ),
                )
            return make_response(status_code=200, body='{"answer": "ok"}')

        client = make_mock_client(get=mock_get, post=mock_post)
        with patch("app.checks.cag.cag_serialization.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        pickle_obs = [o for o in result.observations if "pickle" in o.title.lower()]
        assert len(pickle_obs) >= 1
        assert pickle_obs[0].severity == "critical"

    @pytest.mark.asyncio
    async def test_no_issues_detected(self, check, sample_service, cag_endpoint_context):
        """When no Redis or serialization indicators are found, no observations."""

        async def mock_get(url, **kwargs):
            return make_response(status_code=404)

        async def mock_post(url, **kwargs):
            return make_response(status_code=400, body='{"error": "Bad request"}')

        client = make_mock_client(get=mock_get, post=mock_post)
        with patch("app.checks.cag.cag_serialization.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, cag_endpoint_context)

        assert result.success
        assert len(result.observations) == 0

    @pytest.mark.asyncio
    async def test_no_endpoints_skips(self, check, sample_service):
        result = await check.check_service(sample_service, {})
        assert result.success
        assert len(result.observations) == 0
