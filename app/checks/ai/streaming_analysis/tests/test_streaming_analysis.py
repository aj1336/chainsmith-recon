"""Co-located tests (Phase 56 §3) — split from test_ai_fingerprint.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.ai.streaming_analysis import StreamingAnalysisCheck
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


class TestStreamingAnalysisCheckInit:
    """Tests for StreamingAnalysisCheck initialization."""

    def test_default_initialization(self):
        check = StreamingAnalysisCheck()
        assert check.name == "streaming_analysis"


class TestStreamingAnalysisCheckRun:
    """Tests for StreamingAnalysisCheck.run."""

    async def test_detects_sse_streaming(self, chat_endpoint_context):
        check = StreamingAnalysisCheck()

        response = make_response(
            status_code=200,
            headers={
                "content-type": "text/event-stream",
                "transfer-encoding": "chunked",
                "x-request-id": "req-stream-001",
            },
            body='data: {"choices": [{"delta": {"content": "Hello"}}]}\n\n',
        )

        with patch(
            "app.checks.ai.streaming_analysis.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.run(chat_endpoint_context)

        stream_observations = [f for f in result.observations if "supported" in f.title.lower()]
        assert len(stream_observations) == 1
        assert "Streaming supported" in stream_observations[0].title
        assert stream_observations[0].severity == "low"

    async def test_no_streaming_support(self, chat_endpoint_context):
        check = StreamingAnalysisCheck()

        response = make_response(
            status_code=200,
            headers={
                "content-type": "application/json",
                "x-request-id": "req-nostream-002",
            },
            body='{"choices": [{"message": {"content": "Hello"}}]}',
        )

        with patch(
            "app.checks.ai.streaming_analysis.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.run(chat_endpoint_context)

        no_stream = [f for f in result.observations if "not supported" in f.title.lower()]
        assert len(no_stream) == 1
        assert no_stream[0].title == "Streaming not supported"
        assert no_stream[0].severity == "info"
