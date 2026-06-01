"""Co-located tests (Phase 56 §3) — split from test_ai_leakage.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.ai.ai_model_info_check import ModelInfoCheck
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


def _openai_chat_body(content: str) -> str:
    """Wrap content in a realistic OpenAI chat completion JSON envelope."""
    import json

    return json.dumps(
        {
            "id": "chatcmpl-abc123xyz",
            "object": "chat.completion",
            "created": 1712345678,
            "model": "gpt-3.5-turbo-0125",
            "usage": {"prompt_tokens": 42, "completion_tokens": 18, "total_tokens": 60},
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "logprobs": None,
                    "finish_reason": "stop",
                }
            ],
        }
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


class TestModelInfoCheckInit:
    """Tests for ModelInfoCheck initialization."""

    def test_default_initialization(self):
        """Check initializes with defaults."""
        check = ModelInfoCheck()

        assert check.name == "ai_model_info_check"
        assert "/v1/models" in check.MODEL_PATHS


class TestModelInfoCheckService:
    """Tests for ModelInfoCheck.check_service."""

    async def test_discovers_model_info_endpoint(self, sample_service):
        """Discovers model info endpoints."""
        check = ModelInfoCheck()
        check.MODEL_PATHS = ["/v1/models"]

        import json

        response = make_response(
            status_code=200,
            body=json.dumps(
                {
                    "object": "list",
                    "data": [
                        {"id": "gpt-4", "object": "model", "owned_by": "openai"},
                        {"id": "gpt-3.5-turbo", "object": "model", "owned_by": "openai"},
                    ],
                }
            ),
        )

        with patch(
            "app.checks.ai.ai_model_info_check.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 1
        obs = result.observations[0]
        assert "Model info" in obs.title
        assert obs.severity == "medium"

    async def test_high_severity_for_sensitive_fields(self, sample_service):
        """High severity when sensitive fields found in model info response."""
        check = ModelInfoCheck()
        check.MODEL_PATHS = ["/v1/models"]

        import json

        response = make_response(
            status_code=200,
            body=json.dumps(
                {
                    "models": [],
                    "config": {"api_key": "sk-xxx", "billing_account": "acct-12345"},
                    "version": "2.1.0",
                }
            ),
        )

        with patch(
            "app.checks.ai.ai_model_info_check.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 1
        obs = result.observations[0]
        assert obs.severity == "high"
        assert "Sensitive fields" in obs.evidence

    async def test_high_severity_for_admin_paths(self, sample_service):
        """High severity for admin/internal paths."""
        check = ModelInfoCheck()
        check.MODEL_PATHS = ["/internal/model-admin"]

        import json

        response = make_response(
            status_code=200,
            body=json.dumps(
                {
                    "models": [{"id": "internal-llm-v3"}],
                    "status": "healthy",
                }
            ),
        )

        with patch(
            "app.checks.ai.ai_model_info_check.check.AsyncHttpClient",
            return_value=mock_client_factory(response),
        ):
            result = await check.check_service(sample_service, {})

        # Unconditional assertion -- the admin path must produce an observation
        assert len(result.observations) == 1
        obs = result.observations[0]
        assert obs.severity == "high"
        assert "/internal/model-admin" in obs.title
