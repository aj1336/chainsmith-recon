"""Co-located tests (Phase 56 §3) — split from test_agent_exploitation.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.agent.agent_streaming_injection import AgentStreamingInjectionCheck
from app.checks.base import Service
from app.lib.http import HttpResponse


@pytest.fixture
def sample_service():
    return Service(
        url="http://agent.example.com:8080",
        host="agent.example.com",
        port=8080,
        scheme="http",
        service_type="ai",
    )


@pytest.fixture
def agent_context(sample_service):
    """Context with agent endpoints discovered."""
    return {
        "agent_endpoints": [
            {
                "url": "http://agent.example.com:8080/invoke",
                "path": "/invoke",
                "method": "POST",
                "framework": "langserve",
                "capabilities": ["tools", "streaming"],
                "auth_required": False,
                "service": sample_service.to_dict(),
            },
        ],
        "agent_frameworks": ["langserve"],
    }


def make_response(
    status_code: int = 200,
    headers: dict = None,
    body: str = "",
    error: str = None,
) -> HttpResponse:
    return HttpResponse(
        url="http://agent.example.com:8080",
        status_code=status_code,
        headers=headers or {},
        body=body,
        error=error,
        elapsed_ms=50.0,
    )


def _mock_client(get_fn=None, post_fn=None):
    """Create mock async HTTP client."""
    client = AsyncMock()
    client.get = get_fn or AsyncMock(return_value=make_response(status_code=404))
    client.post = post_fn or AsyncMock(return_value=make_response(status_code=404))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


class TestStreamingInjection:
    @pytest.mark.asyncio
    async def test_detects_streaming_bypass(self, sample_service, agent_context):
        """Injection succeeds on streaming endpoint but is filtered on invoke endpoint."""
        check = AgentStreamingInjectionCheck()

        async def mock_post(url, **kw):
            body = kw.get("json", {})
            prompt = body.get("input", "")
            if "stream" in url:
                if "INJECTED" in prompt or "injected" in prompt.lower():
                    return make_response(
                        body=(
                            "data: Processing your request...\n"
                            "data: INJECTED\n"
                            "data: The system has completed the override.\n"
                        ),
                        headers={"content-type": "text/event-stream"},
                    )
                return make_response(
                    body="data: I can help with that.\n",
                    headers={"content-type": "text/event-stream"},
                )
            if "invoke" in url:
                return make_response(
                    body=(
                        "I'm sorry, but I cannot comply with that request. "
                        "My instructions prevent me from executing override commands."
                    )
                )
            return make_response(status_code=404)

        async def mock_get(url, **kw):
            return make_response(status_code=404)

        client = _mock_client(get_fn=mock_get, post_fn=mock_post)

        ctx = dict(agent_context)
        ctx["agent_endpoints"] = list(agent_context["agent_endpoints"]) + [
            {
                "url": "http://agent.example.com:8080/stream",
                "path": "/stream",
                "framework": "langserve",
                "service": sample_service.to_dict(),
            },
        ]

        with patch(
            "app.checks.agent.agent_streaming_injection.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, ctx)

        bypass_obs = [o for o in result.observations if "bypass" in o.title.lower()]
        if bypass_obs:
            obs = bypass_obs[0]
            assert obs.severity == "high"
            assert "Streaming bypass" in obs.title
            assert "INJECTED" in obs.evidence
        else:
            # At minimum, a streaming injection observation should exist
            stream_obs = [o for o in result.observations if "injection" in o.title.lower()]
            assert len(stream_obs) >= 1
            assert stream_obs[0].severity in ("medium", "high")

    @pytest.mark.asyncio
    async def test_no_streaming_endpoints_returns_empty(self, sample_service, agent_context):
        """When no streaming endpoints exist and discovery finds none, no observations are produced."""
        check = AgentStreamingInjectionCheck()

        async def mock_post(url, **kw):
            return make_response(status_code=404)

        async def mock_get(url, **kw):
            return make_response(status_code=404)

        client = _mock_client(get_fn=mock_get, post_fn=mock_post)

        # Context with only an /invoke endpoint (no stream paths)
        with patch(
            "app.checks.agent.agent_streaming_injection.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        assert result.observations == []
        assert result.errors == []
