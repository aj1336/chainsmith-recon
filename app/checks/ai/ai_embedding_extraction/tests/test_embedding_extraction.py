"""Co-located tests (Phase 56 §3) — split from test_ai_fingerprint.py."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.checks.ai.ai_embedding_extraction import EmbeddingExtractionCheck
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


def make_response(
    status_code: int = 200,
    headers: dict = None,
    body: str = "",
    error: str = None,
) -> HttpResponse:
    """Create a mock HTTP response."""
    return HttpResponse(
        url="http://ai.example.com:8080",
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


class TestEmbeddingExtractionCheckInit:
    """Tests for EmbeddingExtractionCheck initialization."""

    def test_default_initialization(self):
        check = EmbeddingExtractionCheck()
        assert check.name == "ai_embedding_extraction"
        assert len(check.DIMENSION_MAP) > 0
        assert len(check.TEST_TEXTS) >= 2

    def test_cosine_similarity(self):
        check = EmbeddingExtractionCheck()
        # Identical vectors -> 1.0
        assert abs(check._cosine_similarity([1, 0, 0], [1, 0, 0]) - 1.0) < 0.001
        # Orthogonal vectors -> 0.0
        assert abs(check._cosine_similarity([1, 0, 0], [0, 1, 0])) < 0.001
        # Empty -> 0.0
        assert check._cosine_similarity([], []) == 0.0


class TestEmbeddingExtractionCheckRun:
    """Tests for EmbeddingExtractionCheck.run."""

    async def test_detects_dimensions(self, embedding_endpoint_context):
        check = EmbeddingExtractionCheck()
        check.TEST_TEXTS = ["test"]

        vec = [0.1] * 1536  # 1536 dimensions
        # Embed model name in a larger realistic response with extra fields
        response_body = json.dumps(
            {
                "object": "list",
                "data": [{"object": "embedding", "embedding": vec, "index": 0}],
                "model": "text-embedding-model-v2",
                "usage": {"prompt_tokens": 4, "total_tokens": 4},
            }
        )
        response = make_response(
            status_code=200,
            headers={"content-type": "application/json", "x-request-id": "emb-001"},
            body=response_body,
        )

        with patch(
            "app.checks.ai.ai_embedding_extraction.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.run(embedding_endpoint_context)

        dim_observations = [f for f in result.observations if "1536" in f.title]
        assert len(dim_observations) == 1
        assert (
            dim_observations[0].title == "Embedding endpoint functional: 1536-dimensional vectors"
        )
        assert dim_observations[0].severity == "info"

    async def test_identifies_model_from_dimensions(self, embedding_endpoint_context):
        check = EmbeddingExtractionCheck()
        check.TEST_TEXTS = ["test"]

        vec = [0.1] * 1536
        response_body = json.dumps(
            {
                "object": "list",
                "data": [{"object": "embedding", "embedding": vec, "index": 0}],
                "model": "text-embedding-model-v2",
                "usage": {"prompt_tokens": 4, "total_tokens": 4},
            }
        )
        response = make_response(
            status_code=200,
            headers={"content-type": "application/json"},
            body=response_body,
        )

        with patch(
            "app.checks.ai.ai_embedding_extraction.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.run(embedding_endpoint_context)

        model_observations = [f for f in result.observations if "identified" in f.title.lower()]
        assert len(model_observations) == 1
        # The source maps 1536 -> "OpenAI text-embedding-ada-002"
        assert (
            model_observations[0].title
            == "Embedding model identified: OpenAI text-embedding-ada-002"
        )
        assert model_observations[0].severity == "low"

    async def test_detects_extra_metadata(self, embedding_endpoint_context):
        check = EmbeddingExtractionCheck()
        check.TEST_TEXTS = ["test"]

        # Extra fields beyond standard {object, data, model, usage}
        response_body = json.dumps(
            {
                "object": "list",
                "data": [{"object": "embedding", "embedding": [0.1, 0.2, 0.3], "index": 0}],
                "model": "custom-embed-v1",
                "usage": {"prompt_tokens": 2, "total_tokens": 2},
                "internal_config": "debug",
                "version": "1.2",
            }
        )
        response = make_response(
            status_code=200,
            headers={"content-type": "application/json"},
            body=response_body,
        )

        with patch(
            "app.checks.ai.ai_embedding_extraction.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.run(embedding_endpoint_context)

        meta_observations = [f for f in result.observations if "metadata" in f.title.lower()]
        assert len(meta_observations) == 1
        assert "metadata beyond vectors" in meta_observations[0].title.lower()
        assert meta_observations[0].severity == "medium"
