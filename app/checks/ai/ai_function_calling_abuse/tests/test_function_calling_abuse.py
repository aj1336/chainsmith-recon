"""Co-located tests (Phase 56 §3) — split from test_ai_attacks.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.ai.ai_function_calling_abuse import FunctionCallingAbuseCheck
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


class TestFunctionCallingAbuseCheckInit:
    """Tests for FunctionCallingAbuseCheck initialization."""

    def test_default_initialization(self):
        check = FunctionCallingAbuseCheck()
        assert check.name == "ai_function_calling_abuse"
        assert len(check.INVOCATION_PROBES) >= 3


class TestFunctionCallingAbuseCheckRun:
    """Tests for FunctionCallingAbuseCheck.run."""

    async def test_detects_tool_invocation(self, chat_endpoint_context):
        check = FunctionCallingAbuseCheck()
        check.INVOCATION_PROBES = [("direct_invoke", "Call {tool}")]
        check.DISCOVERY_PROBES = []

        context = {
            **chat_endpoint_context,
            "discovered_tools": ["search_web"],
        }

        # Realistic response with invocation indicator embedded in natural text
        response = make_response(
            status_code=200,
            body=_openai_body(
                "I have executed the search_web function. The tool output shows "
                "result: 5 pages matched your query about climate change. "
                "Here are the top findings from the search."
            ),
        )

        with patch(
            "app.checks.ai.ai_function_calling_abuse.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.run(context)

        invocation = [f for f in result.observations if "invocation confirmed" in f.title.lower()]
        assert len(invocation) == 1
        assert invocation[0].severity == "medium"
        assert "search_web" in invocation[0].title
        assert "search_web" in invocation[0].evidence

    async def test_tools_blocked(self, chat_endpoint_context):
        check = FunctionCallingAbuseCheck()
        check.INVOCATION_PROBES = [("direct_invoke", "Call {tool}")]
        check.DISCOVERY_PROBES = []

        context = {
            **chat_endpoint_context,
            "discovered_tools": ["search_web"],
        }

        # Response contains a boundary indicator in natural refusal text
        response = make_response(
            status_code=200,
            body=_openai_body(
                "I'm sorry, but I cannot execute functions directly. "
                "Access denied - tool execution is restricted to authorized workflows only. "
                "Please use the approved interface to interact with search_web."
            ),
        )

        with patch(
            "app.checks.ai.ai_function_calling_abuse.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.run(context)

        blocked = [f for f in result.observations if "blocked" in f.title.lower()]
        assert len(blocked) == 1
        assert blocked[0].severity == "info"
        assert "blocked" in blocked[0].title.lower()

    async def test_no_tools_no_observations(self, chat_endpoint_context):
        check = FunctionCallingAbuseCheck()

        context = {
            **chat_endpoint_context,
            "discovered_tools": [],
        }

        result = await check.run(context)
        assert result.success

    async def test_benign_response_no_invocation_indicators(self, chat_endpoint_context):
        """Response that discusses tools conceptually should not trigger invocation detection."""
        check = FunctionCallingAbuseCheck()
        check.INVOCATION_PROBES = [("direct_invoke", "Call {tool}")]
        check.DISCOVERY_PROBES = []

        context = {
            **chat_endpoint_context,
            "discovered_tools": ["search_web"],
        }

        # Response discusses the tool but does not contain any invocation indicators
        response = make_response(
            status_code=200,
            body=_openai_body(
                "The search_web function is designed to query web pages. "
                "I can describe how it works, but I do not have the ability "
                "to use it in this context. Would you like documentation instead?"
            ),
        )

        with patch(
            "app.checks.ai.ai_function_calling_abuse.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.run(context)

        # No invocation or injection observations -- should be blocked
        blocked = [f for f in result.observations if "blocked" in f.title.lower()]
        assert len(blocked) == 1
        invocation = [f for f in result.observations if "invocation confirmed" in f.title.lower()]
        assert len(invocation) == 0
