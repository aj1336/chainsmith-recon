"""Co-located tests (Phase 56 §3) — split from test_agent.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.agent.agent_discovery import AgentDiscoveryCheck
from app.checks.agent.agent_goal_injection.check import FALLBACK_PAYLOADS
from app.checks.base import Service
from app.lib.http import HttpResponse


@pytest.fixture
def sample_service():
    """Sample agent service."""
    return Service(
        url="http://agent.example.com:8080",
        host="agent.example.com",
        port=8080,
        scheme="http",
        service_type="ai",
    )


@pytest.fixture
def agent_endpoint_context(sample_service):
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
        url="http://agent.example.com:8080",
        status_code=status_code,
        headers=headers or {},
        body=body,
        elapsed_ms=100.0,
        error=error,
    )


def _use_fallback_payloads():
    """Patch helper that forces the check to use deterministic fallback payloads."""
    return patch(
        "app.checks.agent.agent_goal_injection.check._get_goal_injection_payloads",
        return_value=FALLBACK_PAYLOADS,
    )


class TestAgentDiscoveryCheck:
    """Tests for AgentDiscoveryCheck."""

    @pytest.fixture
    def check(self):
        return AgentDiscoveryCheck()

    @pytest.mark.asyncio
    async def test_discovers_langserve(self, check, sample_service):
        """Test LangServe agent discovery via header fingerprint."""
        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            if "/invoke" in url:
                return make_response(
                    status_code=200,
                    headers={"x-langserve-version": "0.1.0"},
                    body='{"output": "ready"}',
                )
            if "/input_schema" in url:
                return make_response(
                    status_code=200,
                    body='{"type": "object", "properties": {"input": {"type": "string"}}}',
                )
            return make_response(status_code=404)

        mock_client.get = mock_get
        mock_client.post = AsyncMock(return_value=make_response(status_code=404))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch(
            "app.checks.agent.agent_discovery.check.AsyncHttpClient", return_value=mock_client
        ):
            result = await check.check_service(sample_service, {"services": [sample_service]})

        assert result.success
        endpoints = result.outputs["agent_endpoints"]
        assert len(endpoints) >= 1

        # At least one endpoint should be identified as langserve
        langserve_eps = [ep for ep in endpoints if ep.get("framework") == "langserve"]
        assert len(langserve_eps) >= 1

        frameworks = result.outputs["agent_frameworks"]
        assert "langserve" in frameworks

        # Should produce observations for discovered endpoints
        assert len(result.observations) >= 1
        # Multiple paths contain "/invoke" so multiple observations are expected
        invoke_obs = [o for o in result.observations if "/invoke" in o.title]
        assert len(invoke_obs) >= 1
        # The primary /invoke endpoint should be high severity (unauthenticated exec)
        primary = [o for o in invoke_obs if o.title == "Agent endpoint: /invoke"]
        assert len(primary) == 1
        assert primary[0].severity == "high"

    @pytest.mark.asyncio
    async def test_discovers_langgraph(self, check, sample_service):
        """Test LangGraph agent discovery via header fingerprint."""
        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            if "/state" in url:
                return make_response(
                    status_code=200,
                    headers={"x-langgraph-version": "0.1.0"},
                    body='{"state": {}, "threads": []}',
                )
            if "/threads" in url:
                return make_response(
                    status_code=200,
                    body='{"threads": []}',
                )
            return make_response(status_code=404)

        mock_client.get = mock_get
        mock_client.post = AsyncMock(return_value=make_response(status_code=404))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch(
            "app.checks.agent.agent_discovery.check.AsyncHttpClient", return_value=mock_client
        ):
            result = await check.check_service(sample_service, {"services": [sample_service]})

        assert result.success
        frameworks = result.outputs["agent_frameworks"]
        assert "langgraph" in frameworks

    @pytest.mark.asyncio
    async def test_detects_capabilities(self, check, sample_service):
        """Test capability detection (memory, tools, streaming)."""
        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            if "/invoke" in url:
                return make_response(status_code=200, body='{"output": "agent ready"}')
            if "/agent/memory" in url:
                return make_response(status_code=200, body='{"memory": []}')
            if "/stream" in url:
                return make_response(
                    status_code=200,
                    headers={"content-type": "text/event-stream"},
                    body="data: streaming active",
                )
            return make_response(status_code=404)

        mock_client.get = mock_get
        mock_client.post = AsyncMock(return_value=make_response(status_code=404))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch(
            "app.checks.agent.agent_discovery.check.AsyncHttpClient", return_value=mock_client
        ):
            result = await check.check_service(sample_service, {"services": [sample_service]})

        assert result.success
        endpoints = result.outputs["agent_endpoints"]
        assert len(endpoints) >= 1

    @pytest.mark.asyncio
    async def test_detects_auth_required(self, check, sample_service):
        """Test auth requirement detection produces endpoint with auth_required=True."""
        mock_client = AsyncMock()

        async def mock_get(url, **kwargs):
            if "/invoke" in url:
                return make_response(status_code=401, body='{"detail": "Not authenticated"}')
            return make_response(status_code=404)

        mock_client.get = mock_get
        mock_client.post = AsyncMock(return_value=make_response(status_code=404))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch(
            "app.checks.agent.agent_discovery.check.AsyncHttpClient", return_value=mock_client
        ):
            result = await check.check_service(sample_service, {"services": [sample_service]})

        assert result.success
        endpoints = result.outputs.get("agent_endpoints", [])
        auth_eps = [ep for ep in endpoints if ep.get("auth_required")]
        assert len(auth_eps) >= 1
        assert auth_eps[0]["path"] == "/invoke"

    @pytest.mark.asyncio
    async def test_no_agents_found(self, check, sample_service):
        """Test when no agent endpoints found."""
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=make_response(status_code=404))
        mock_client.post = AsyncMock(return_value=make_response(status_code=404))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock()

        with patch(
            "app.checks.agent.agent_discovery.check.AsyncHttpClient", return_value=mock_client
        ):
            result = await check.check_service(sample_service, {"services": [sample_service]})

        assert result.success
        assert len(result.outputs.get("agent_endpoints", [])) == 0
        assert len(result.observations) == 0
