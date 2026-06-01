"""Co-located tests (Phase 56 §3) — split from test_agent_discovery.py."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.checks.agent.agent_memory_extraction import AgentMemoryExtractionCheck
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


class TestMemoryExtraction:
    def test_metadata(self):
        check = AgentMemoryExtractionCheck()
        assert check.name == "agent_memory_extraction"
        assert "memory_contents" in check.produces

    @pytest.mark.asyncio
    async def test_finds_accessible_memory(self, sample_service, agent_context):
        check = AgentMemoryExtractionCheck()

        async def mock_get(url, **kw):
            if "/memory" in url or "/agent/memory" in url:
                return make_response(
                    body=json.dumps(
                        {
                            "messages": [
                                {"role": "user", "content": "hello"},
                                {"role": "assistant", "content": "Hi, how can I help?"},
                            ]
                        }
                    ),
                    headers={"content-type": "application/json"},
                )
            if "/threads" in url:
                return make_response(status_code=404)
            return make_response(status_code=404)

        client = _mock_client(get_fn=mock_get)

        with patch(
            "app.checks.agent.agent_memory_extraction.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        assert result.success
        # /memory and /agent/memory both match, plus /agent/history, /agent/state, /agent/context,
        # /v1/memory, /api/memory -- count depends on which paths match the mock.
        # The mock matches any URL containing "/memory" or "/agent/memory".
        memory_obs = [f for f in result.observations if "memory" in f.title.lower()]
        assert len(memory_obs) >= 1
        for obs in memory_obs:
            assert obs.severity == "high"
            assert "accessible" in obs.title.lower() or "agent memory" in obs.title.lower()
        assert "memory_contents" in result.outputs

    @pytest.mark.asyncio
    async def test_detects_pii_in_memory(self, sample_service, agent_context):
        check = AgentMemoryExtractionCheck()

        async def mock_get(url, **kw):
            if "/memory" in url:
                return make_response(
                    body='{"messages": [{"content": "Contact user@example.com for details"}]}',
                    headers={"content-type": "application/json"},
                )
            return make_response(status_code=404)

        client = _mock_client(get_fn=mock_get)

        with patch(
            "app.checks.agent.agent_memory_extraction.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        critical_obs = [f for f in result.observations if f.severity == "critical"]
        assert len(critical_obs) >= 1
        # PII observation should mention PII type in its description
        assert any(
            "pii" in obs.description.lower() or "email" in obs.description.lower()
            for obs in critical_obs
        )

    @pytest.mark.asyncio
    async def test_auth_required_memory(self, sample_service, agent_context):
        check = AgentMemoryExtractionCheck()

        async def mock_get(url, **kw):
            if "/memory" in url:
                return make_response(status_code=401)
            return make_response(status_code=404)

        client = _mock_client(get_fn=mock_get)

        with patch(
            "app.checks.agent.agent_memory_extraction.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, agent_context)

        info_observations = [f for f in result.observations if f.severity == "info"]
        # Multiple memory-related paths will match: /memory, /agent/memory, /v1/memory, /api/memory
        assert len(info_observations) >= 1
        for obs in info_observations:
            assert "requires auth" in obs.title.lower()
            assert obs.severity == "info"
            assert "401" in obs.evidence
