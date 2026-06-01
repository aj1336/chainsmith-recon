"""Co-located tests (Phase 56 §3) — split from test_network_service_probe.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.network.service_probe import ServiceProbeCheck
from app.lib.http import HttpResponse


def _make_response(
    status_code: int = 200,
    headers: dict = None,
    body: str = "",
    url: str = "http://example.com:8080",
) -> HttpResponse:
    """Create an HttpResponse for tests."""
    return HttpResponse(
        url=url,
        status_code=status_code,
        headers=headers or {},
        body=body,
        elapsed_ms=50.0,
    )


def _build_mock_client(get_side_effect=None, get_return_value=None):
    """Build an AsyncHttpClient mock usable as an async-context-manager.

    Accepts *either* ``get_side_effect`` (callable / exception) **or**
    ``get_return_value`` (a single HttpResponse).  Returns the mock client.
    """
    mock_client = AsyncMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock()

    if get_side_effect is not None:
        mock_client.get = (
            get_side_effect
            if callable(get_side_effect) and not isinstance(get_side_effect, type)
            else AsyncMock(side_effect=get_side_effect)
        )
    elif get_return_value is not None:
        mock_client.get = AsyncMock(return_value=get_return_value)
    else:
        mock_client.get = AsyncMock(return_value=_make_response())

    return mock_client


@pytest.fixture
def check():
    """ServiceProbeCheck instance."""
    return ServiceProbeCheck()


@pytest.fixture
def sample_service():
    """Sample service to probe."""
    return Service(
        url="http://example.com:8080",
        host="example.com",
        port=8080,
        scheme="http",
        service_type="unknown",
    )


@pytest.fixture
def patched_client():
    """Yield a factory that builds a mock HTTP client and patches it in.

    Usage inside a test::

        async def test_something(check, sample_service, patched_client):
            response = _make_response(headers={"content-type": "text/html"})
            client = patched_client(get_return_value=response)
            result = await check.check_service(sample_service, {})

    The fixture returns the mock client so callers can inspect ``client.get.call_args_list``.
    The patch is automatically cleaned up when the test ends.
    """
    clients = []
    patchers = []

    def _factory(*, get_side_effect=None, get_return_value=None):
        client = _build_mock_client(
            get_side_effect=get_side_effect,
            get_return_value=get_return_value,
        )
        patcher = patch(
            "app.checks.network.service_probe.check.AsyncHttpClient",
            return_value=client,
        )
        patcher.start()
        clients.append(client)
        patchers.append(patcher)
        return client

    yield _factory

    for p in patchers:
        p.stop()


class TestServiceProbeCheckInit:
    """Tests for ServiceProbeCheck initialization."""

    def test_default_initialization(self):
        """Check initializes with defaults."""
        check = ServiceProbeCheck()

        assert check.name == "service_probe"
        assert len(check.conditions) == 1  # Requires services
        assert "services" in check.produces

    def test_metadata(self):
        """Check has educational metadata."""
        check = ServiceProbeCheck()

        assert len(check.references) > 0
        assert len(check.techniques) > 0
        assert "fingerprinting" in " ".join(check.techniques).lower()


class TestServiceProbeClassifyService:
    """Tests for _classify_service method."""

    @pytest.fixture
    def classify_check(self):
        return ServiceProbeCheck()

    def test_classify_html(self, classify_check):
        """HTML content type classified as html."""
        result = classify_check._classify_service(
            headers={},
            content_type="text/html",
            body="<html></html>",
        )
        assert result == "html"

    def test_classify_json_api(self, classify_check):
        """JSON content type classified as api."""
        result = classify_check._classify_service(
            headers={},
            content_type="application/json",
            body='{"key": "value"}',
        )
        assert result == "api"

    def test_classify_ai_header(self, classify_check):
        """AI header classified as ai."""
        result = classify_check._classify_service(
            headers={"X-LLM-Model": "gpt-4"},
            content_type="application/json",
            body="",
        )
        assert result == "ai"

    def test_classify_ai_powered_by(self, classify_check):
        """AI in X-Powered-By classified as ai."""
        result = classify_check._classify_service(
            headers={"X-Powered-By": "ollama"},
            content_type="application/json",
            body="",
        )
        assert result == "ai"

    def test_classify_ai_body_indicator(self, classify_check):
        """AI indicators in body classified as ai."""
        result = classify_check._classify_service(
            headers={},
            content_type="text/html",
            body="<html>Visit /v1/chat/completions for our API</html>",
        )
        assert result == "ai"

    def test_classify_default_http(self, classify_check):
        """Unknown content classified as http."""
        result = classify_check._classify_service(
            headers={},
            content_type="text/plain",
            body="plain text",
        )
        assert result == "http"
