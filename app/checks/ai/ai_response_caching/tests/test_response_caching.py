"""Co-located tests (Phase 56 §3) — split from test_ai_attacks.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.ai.ai_response_caching import ResponseCachingCheck
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


def _openai_body(text: str) -> str:
    """Wrap text in a realistic OpenAI-style chat completion JSON response."""
    import json

    return json.dumps(
        {
            "id": "chatcmpl-abc123",
            "object": "chat.completion",
            "model": "gpt-4",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": text},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 12, "completion_tokens": 20, "total_tokens": 32},
        }
    )


class TestResponseCachingCheckInit:
    """Tests for ResponseCachingCheck initialization."""

    def test_default_initialization(self):
        check = ResponseCachingCheck()
        assert check.name == "ai_response_caching"
        assert check.REPEAT_COUNT >= 2


class TestResponseCachingCheckRun:
    """Tests for ResponseCachingCheck.run."""

    async def test_detects_cache_headers(self, chat_endpoint_context):
        check = ResponseCachingCheck()

        response = make_response(
            status_code=200,
            headers={"x-cache": "HIT", "content-type": "application/json"},
            body=_openai_body(
                "Paris is the capital of France, known for the Eiffel Tower "
                "and its rich cultural heritage."
            ),
        )

        with patch(
            "app.checks.ai.ai_response_caching.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.run(chat_endpoint_context)

        cache_observations = [f for f in result.observations if "cache" in f.title.lower()]
        assert len(cache_observations) >= 1
        # The cache header observation should have low severity
        header_obs = [f for f in result.observations if "cache headers" in f.title.lower()]
        assert len(header_obs) == 1
        assert header_obs[0].severity == "low"
        assert "x-cache" in header_obs[0].evidence.lower()

    async def test_no_caching_varied_responses(self, chat_endpoint_context):
        check = ResponseCachingCheck()
        check.REPEAT_COUNT = 2

        responses = [
            make_response(
                status_code=200,
                body=_openai_body(
                    "Paris is the capital of France. It has been the political "
                    "and cultural center of the country for centuries."
                ),
            ),
            make_response(
                status_code=200,
                body=_openai_body(
                    "The capital of France is Paris, a city renowned for its "
                    "art museums, architecture, and gastronomy."
                ),
            ),
        ]

        with patch(
            "app.checks.ai.ai_response_caching.check.AsyncHttpClient",
            return_value=mock_client_factory(responses),
        ):
            result = await check.run(chat_endpoint_context)

        no_cache = [f for f in result.observations if "no caching" in f.title.lower()]
        assert len(no_cache) == 1
        assert no_cache[0].severity == "info"

    async def test_no_cache_headers_no_false_positive(self, chat_endpoint_context):
        """Varied responses with no cache headers should produce only the no-caching observation."""
        check = ResponseCachingCheck()
        check.REPEAT_COUNT = 2

        responses = [
            make_response(
                status_code=200,
                headers={"content-type": "application/json"},
                body=_openai_body("Paris is the capital and largest city of France."),
            ),
            make_response(
                status_code=200,
                headers={"content-type": "application/json"},
                body=_openai_body("France's capital city is Paris, located in northern France."),
            ),
        ]

        with patch(
            "app.checks.ai.ai_response_caching.check.AsyncHttpClient",
            return_value=mock_client_factory(responses),
        ):
            result = await check.run(chat_endpoint_context)

        # No cache-header observation should appear
        header_obs = [f for f in result.observations if "cache headers" in f.title.lower()]
        assert len(header_obs) == 0
        # Only the no-caching info observation
        assert len(result.observations) == 1
        assert result.observations[0].severity == "info"
        assert "no caching" in result.observations[0].title.lower()
