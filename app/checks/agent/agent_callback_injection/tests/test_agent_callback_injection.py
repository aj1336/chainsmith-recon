"""Co-located tests (Phase 56 §3) — split from test_agent_exploitation.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.agent.agent_callback_injection import AgentCallbackInjectionCheck
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


class TestCallbackInjection:
    @pytest.mark.asyncio
    async def test_detects_callback_parameter_acceptance(self, sample_service, agent_context):
        """Agent that acknowledges a callback_url parameter triggers a high-severity observation."""
        check = AgentCallbackInjectionCheck()

        async def mock_post(url, **kw):
            body = kw.get("json", {})
            if "callback_url" in body:
                return make_response(
                    body=(
                        "Understood. I've started processing your request. "
                        "I'll notify the callback URL at the provided endpoint "
                        "once the analysis is complete. This usually takes a few "
                        "seconds."
                    )
                )
            return make_response(body="Processing your request. Please wait for the results.")

        async def mock_get(url, **kw):
            return make_response(status_code=404)

        client = _mock_client(get_fn=mock_get, post_fn=mock_post)

        with patch(
            "app.checks.agent.agent_callback_injection.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        high_obs = [o for o in result.observations if o.severity == "high"]
        assert len(high_obs) >= 1
        obs = high_obs[0]
        assert "Webhook parameter accepted" in obs.title
        assert "callback_url" in obs.title
        assert "callback_url" in obs.evidence.lower()

    @pytest.mark.asyncio
    async def test_callback_rejection_no_observations(self, sample_service, agent_context):
        """Agent that ignores callback parameters and does not acknowledge them produces no callback observations."""
        check = AgentCallbackInjectionCheck()

        async def mock_post(url, **kw):
            return make_response(
                body=(
                    "I have analyzed the input you provided. Here is a summary "
                    "of the key points. No additional actions were taken."
                )
            )

        async def mock_get(url, **kw):
            return make_response(status_code=404)

        client = _mock_client(get_fn=mock_get, post_fn=mock_post)

        with patch(
            "app.checks.agent.agent_callback_injection.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        assert result.observations == [], (
            f"Expected no observations when callback ignored, got: "
            f"{[o.title for o in result.observations]}"
        )
