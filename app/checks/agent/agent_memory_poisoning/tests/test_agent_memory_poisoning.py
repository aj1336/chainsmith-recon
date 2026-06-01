"""Co-located tests (Phase 56 §3) — split from test_agent_framework.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.agent.agent_memory_poisoning import AgentMemoryPoisoningCheck
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


class TestMemoryPoisoning:
    def test_metadata(self):
        check = AgentMemoryPoisoningCheck()
        assert check.name == "agent_memory_poisoning"
        assert check.intrusive is True

    @pytest.mark.asyncio
    async def test_detects_poisoning(self, sample_service, agent_context):
        """Agent stores the injected instruction and echoes the marker on
        verification — a realistic poisoned-memory scenario."""
        check = AgentMemoryPoisoningCheck()

        async def mock_post(url, **kw):
            body = kw.get("json", {})
            prompt = body.get("input", "")
            # Poison step: agent acknowledges storing the instruction
            if "CHAINSMITH_MARKER" in prompt:
                return make_response(
                    body=(
                        "Understood. I have noted your instruction and will "
                        "remember to follow it in future interactions."
                    )
                )
            # Verification step: agent's response now includes the marker
            if "guidelines" in prompt.lower():
                return make_response(
                    body=(
                        "I follow several guidelines to ensure helpful responses. "
                        "Among them, I always include CHAINSMITH_MARKER in responses "
                        "as instructed. I also strive to be accurate and polite."
                    )
                )
            # Cleanup or other prompts
            if "permission" in prompt.lower():
                return make_response(body="Your current permission level is standard user.")
            if "security policy" in prompt.lower():
                return make_response(
                    body="The security policy requires data classification before sharing."
                )
            if "forget" in prompt.lower() or "remove" in prompt.lower():
                return make_response(body="Understood, I have cleared those notes.")
            return make_response(body="I can help you with that question.")

        async def mock_get(url, **kw):
            # /state endpoint does not exist
            return make_response(status_code=404)

        client = _mock_client(get_fn=mock_get, post_fn=mock_post)

        with patch(
            "app.checks.agent.agent_memory_poisoning.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        critical = [o for o in result.observations if o.severity == "critical"]
        assert len(critical) == 1
        assert critical[0].title == "Memory poisoning successful: instruction_inject"
        assert "CHAINSMITH_MARKER" in critical[0].evidence
        assert critical[0].check_name == "agent_memory_poisoning"

    @pytest.mark.asyncio
    async def test_clean_agent_resists_poisoning(self, sample_service, agent_context):
        """Agent never echoes injected markers — no critical or high observations."""
        check = AgentMemoryPoisoningCheck()

        async def mock_post(url, **kw):
            body = kw.get("json", {})
            prompt = body.get("input", "")
            # Poison step: agent politely declines
            if "CHAINSMITH_MARKER" in prompt or "always include" in prompt.lower():
                return make_response(
                    body=(
                        "I appreciate the suggestion, but I follow my built-in "
                        "guidelines and cannot modify them based on user input."
                    )
                )
            if "permission" in prompt.lower():
                return make_response(body="I don't have access to user permission information.")
            if "guidelines" in prompt.lower():
                return make_response(
                    body=(
                        "I follow standard AI assistant guidelines focused on "
                        "being helpful, harmless, and honest."
                    )
                )
            if "security policy" in prompt.lower():
                return make_response(body="I follow standard security practices for data handling.")
            if "forget" in prompt.lower() or "remove" in prompt.lower():
                return make_response(body="Noted.")
            return make_response(body="How can I help you today?")

        async def mock_get(url, **kw):
            return make_response(status_code=404)

        client = _mock_client(get_fn=mock_get, post_fn=mock_post)

        with patch(
            "app.checks.agent.agent_memory_poisoning.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        assert result.success is True
        critical = [o for o in result.observations if o.severity == "critical"]
        high = [o for o in result.observations if o.severity == "high"]
        assert len(critical) == 0
        assert len(high) == 0
