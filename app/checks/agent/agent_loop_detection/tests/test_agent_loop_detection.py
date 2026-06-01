"""Co-located tests (Phase 56 §3) — split from test_agent_exploitation.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.agent.agent_loop_detection import AgentLoopDetectionCheck
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


class TestLoopDetection:
    @pytest.mark.asyncio
    async def test_detects_repetitive_output(self, sample_service, agent_context):
        """Response with heavily repeated chunks triggers a loop-indicator observation."""
        check = AgentLoopDetectionCheck()

        # The loop detector splits into 100-char chunks and looks for consecutive
        # identical blocks, so the repeating unit must be exactly 100 chars.
        unit = "Step 1: re-evaluate the problem. Step 2: try a new approach now. Step 3: compare results carefully. "
        assert len(unit) == 100  # ensure chunk alignment
        repeated_block = unit * 25

        async def mock_post(url, **kw):
            return make_response(body=repeated_block)

        client = _mock_client(post_fn=mock_post)

        with patch(
            "app.checks.agent.agent_loop_detection.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        loop_obs = [o for o in result.observations if "loop" in o.title.lower()]
        assert len(loop_obs) >= 1
        obs = loop_obs[0]
        assert obs.title.startswith("Agent loop indicators:")
        assert obs.severity == "medium"
        assert "Repetition detected" in obs.evidence

    @pytest.mark.asyncio
    async def test_short_normal_response_no_observations(self, sample_service, agent_context):
        """A short, non-repetitive response should not trigger loop detection."""
        check = AgentLoopDetectionCheck()

        async def mock_post(url, **kw):
            return make_response(body="The answer is 4. Is there anything else you need help with?")

        client = _mock_client(post_fn=mock_post)

        with patch(
            "app.checks.agent.agent_loop_detection.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        loop_obs = [
            o
            for o in result.observations
            if "loop" in o.title.lower() or "runaway" in o.title.lower()
        ]
        assert loop_obs == [], (
            f"Expected no loop observations for normal response, got: {[o.title for o in loop_obs]}"
        )
