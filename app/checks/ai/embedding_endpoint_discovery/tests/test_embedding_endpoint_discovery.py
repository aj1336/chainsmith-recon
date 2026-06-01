"""Co-located tests (Phase 56 §3) — split from test_ai_endpoints.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.ai.embedding_endpoint_discovery import EmbeddingEndpointCheck
from app.checks.base import Service
from app.lib.http import HttpResponse


@pytest.fixture
def sample_service():
    """Sample AI service."""
    return Service(
        url="http://ai.example.com:8080",
        host="ai.example.com",
        port=8080,
        scheme="http",
        service_type="ai",
    )


@pytest.fixture
def chat_endpoint_context(sample_service):
    """Context with chat endpoints discovered."""
    return {
        "chat_endpoints": [
            {
                "url": "http://ai.example.com:8080/v1/chat/completions",
                "path": "/v1/chat/completions",
                "service": sample_service.to_dict(),
                "api_format": "openai",
            }
        ]
    }


def make_response(
    status_code: int = 200,
    headers: dict = None,
    body: str = "",
    error: str = None,
    url: str = "http://ai.example.com:8080",
) -> HttpResponse:
    """Create a mock HTTP response."""
    return HttpResponse(
        url=url,
        status_code=status_code,
        headers=headers or {},
        body=body,
        elapsed_ms=50.0,
        error=error,
    )


def mock_client_factory(responses: list[HttpResponse] | HttpResponse | dict = None):
    """Create a mock AsyncHttpClient.

    Args:
        responses: Either a list of responses to return in order,
                   a single response, or a dict mapping paths to responses.
    """
    if responses is None:
        responses = [make_response()]
    elif isinstance(responses, HttpResponse):
        responses = [responses]

    if isinstance(responses, dict):
        path_map = responses

        async def get_by_path(url, *args, **kwargs):
            for path, resp in path_map.items():
                if path in url:
                    return resp
            return make_response(status_code=404)

        mock = AsyncMock()
        mock.__aenter__ = AsyncMock(return_value=mock)
        mock.__aexit__ = AsyncMock()
        mock.get = AsyncMock(side_effect=get_by_path)
        mock.post = AsyncMock(side_effect=get_by_path)
        mock.options = AsyncMock(side_effect=get_by_path)
        return mock

    response_iter = iter(responses)

    async def get_next(*args, **kwargs):
        try:
            return next(response_iter)
        except StopIteration:
            return responses[-1]

    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock()
    mock.get = AsyncMock(side_effect=get_next)
    mock.post = AsyncMock(side_effect=get_next)
    mock.options = AsyncMock(side_effect=get_next)
    mock.head = AsyncMock(side_effect=get_next)

    return mock


@pytest.fixture
def embedding_endpoint_context(sample_service):
    """Context with embedding endpoints discovered."""
    return {
        "embedding_endpoints": [
            {
                "url": "http://ai.example.com:8080/v1/embeddings",
                "path": "/v1/embeddings",
                "service": sample_service.to_dict(),
                "api_format": "openai",
            }
        ]
    }


class TestEmbeddingEndpointCheck:
    """Tests for EmbeddingEndpointCheck."""

    async def test_discovers_embedding_endpoint_with_correct_observation(self, sample_service):
        """Discovers accessible embedding endpoint with correct title, severity, evidence."""
        check = EmbeddingEndpointCheck()
        check.EMBEDDING_PATHS = ["/v1/embeddings"]

        response = make_response(status_code=200, body='{"data": []}')

        with patch(
            "app.checks.ai.embedding_endpoint_discovery.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 1
        obs = result.observations[0]
        assert obs.title == "Embedding endpoint: /v1/embeddings"
        assert obs.severity == "info"
        assert obs.description == "Embedding/vector endpoint discovered"
        assert "POST /v1/embeddings -> HTTP 200" in obs.evidence
        assert obs.target_url == "http://ai.example.com:8080/v1/embeddings"
        assert obs.check_name == "embedding_endpoint_discovery"

        assert "embedding_endpoints" in result.outputs
        endpoints = result.outputs["embedding_endpoints"]
        assert len(endpoints) == 1
        assert endpoints[0]["url"] == "http://ai.example.com:8080/v1/embeddings"
        assert endpoints[0]["path"] == "/v1/embeddings"
        assert endpoints[0]["service"]["host"] == "ai.example.com"

    async def test_skips_404_embedding_endpoint(self, sample_service):
        """POST returning 404 on embedding path produces no observations."""
        check = EmbeddingEndpointCheck()
        check.EMBEDDING_PATHS = ["/v1/embeddings"]

        response = make_response(status_code=404)

        with patch(
            "app.checks.ai.embedding_endpoint_discovery.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 0
        assert "embedding_endpoints" not in result.outputs

    async def test_skips_405_embedding_endpoint(self, sample_service):
        """POST returning 405 on embedding path produces no observations."""
        check = EmbeddingEndpointCheck()
        check.EMBEDDING_PATHS = ["/v1/embeddings"]

        response = make_response(status_code=405)

        with patch(
            "app.checks.ai.embedding_endpoint_discovery.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 0
        assert "embedding_endpoints" not in result.outputs

    async def test_skips_embedding_on_error(self, sample_service):
        """Connection error on embedding path produces no observations."""
        check = EmbeddingEndpointCheck()
        check.EMBEDDING_PATHS = ["/v1/embeddings"]

        response = make_response(status_code=0, error="Timeout")

        with patch(
            "app.checks.ai.embedding_endpoint_discovery.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 0
        assert "embedding_endpoints" not in result.outputs

    async def test_non_ai_body_on_embedding_path_still_registers(self, sample_service):
        """Non-embedding JSON on an embedding path still produces an observation
        because the check does not inspect response body content."""
        check = EmbeddingEndpointCheck()
        check.EMBEDDING_PATHS = ["/v1/embeddings"]

        response = make_response(status_code=200, body='{"message": "not found"}')

        with patch(
            "app.checks.ai.embedding_endpoint_discovery.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 1
        obs = result.observations[0]
        assert obs.title == "Embedding endpoint: /v1/embeddings"
        assert obs.severity == "info"
