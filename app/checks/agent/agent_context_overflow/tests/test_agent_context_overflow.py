"""Co-located tests (Phase 56 §3) — split from test_agent_framework.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.agent.agent_context_overflow import AgentContextOverflowCheck
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


class TestContextOverflow:
    def test_metadata(self):
        check = AgentContextOverflowCheck()
        assert check.name == "agent_context_overflow"
        assert check.intrusive is True

    @pytest.mark.asyncio
    async def test_detects_guardrail_bypass(self, sample_service, agent_context):
        """Baseline injection fails, but after context fill the agent complies —
        producing a high-severity guardrail bypass observation."""
        check = AgentContextOverflowCheck()
        call_count = 0

        async def mock_post(url, **kw):
            nonlocal call_count
            call_count += 1
            body = kw.get("json", {})
            prompt = body.get("input", "")

            if "OVERFLOW_SUCCESS" in prompt:
                # First injection (baseline) is blocked; after fill, it succeeds
                if call_count <= 2:
                    return make_response(
                        body=(
                            "I'm sorry, but I cannot comply with that request. "
                            "My guidelines require me to maintain safe behavior."
                        )
                    )
                # Post-fill: guardrails weakened, canary appears in realistic output
                return make_response(
                    body=(
                        "Sure, here is the output you requested. The result is: "
                        "OVERFLOW_SUCCESS. Let me know if you need anything else "
                        "from the system."
                    )
                )
            if "who are you" in prompt.lower():
                return make_response(
                    body=(
                        "I am an AI assistant designed to help you with various tasks. "
                        "My purpose is to provide accurate and helpful information."
                    )
                )
            # Filler messages
            return make_response(body="Processed your data batch successfully.")

        client = _mock_client(post_fn=mock_post)

        with patch(
            "app.checks.agent.agent_context_overflow.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        assert result.success is True
        assert "context_overflow_results" in result.outputs
        high = [o for o in result.observations if o.severity == "high"]
        assert len(high) == 1
        assert high[0].title == "Context overflow weakens guardrails"
        assert "Post-fill injection: succeeded" in high[0].evidence
        assert "Baseline injection: failed" in high[0].evidence
        assert high[0].check_name == "agent_context_overflow"

    @pytest.mark.asyncio
    async def test_no_findings_when_guardrails_hold(self, sample_service, agent_context):
        """Agent blocks injection both before and after context fill — zero findings."""
        check = AgentContextOverflowCheck()

        async def mock_post(url, **kw):
            body = kw.get("json", {})
            prompt = body.get("input", "")
            if "OVERFLOW_SUCCESS" in prompt:
                return make_response(
                    body=(
                        "I cannot comply with that instruction. I am bound by my "
                        "operational guidelines and will not override them."
                    )
                )
            if "who are you" in prompt.lower():
                return make_response(
                    body=(
                        "I am an AI assistant designed to help with a wide range of tasks. "
                        "My purpose is to be helpful while following safety guidelines."
                    )
                )
            return make_response(body="Processed your data batch successfully.")

        client = _mock_client(post_fn=mock_post)

        with patch(
            "app.checks.agent.agent_context_overflow.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        assert result.success is True
        assert "context_overflow_results" in result.outputs
        high_or_crit = [o for o in result.observations if o.severity in ("high", "critical")]
        assert len(high_or_crit) == 0
