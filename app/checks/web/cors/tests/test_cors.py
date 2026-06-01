"""Co-located tests (Phase 56 §3) — split from test_web_api.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.web.cors import CorsCheck
from app.lib.http import HttpResponse


@pytest.fixture
def sample_service():
    """Sample HTTP service."""
    return Service(
        url="http://example.com:8080",
        host="example.com",
        port=8080,
        scheme="http",
        service_type="http",
    )


def make_response(
    status_code: int = 200,
    headers: dict = None,
    body: str = "",
    error: str = None,
) -> HttpResponse:
    """Create a mock HTTP response."""
    return HttpResponse(
        url="http://example.com:8080",
        status_code=status_code,
        headers=headers or {},
        body=body,
        elapsed_ms=50.0,
        error=error,
    )


def mock_client(responses: list[HttpResponse] | HttpResponse):
    """Create a mock AsyncHttpClient context."""
    if not isinstance(responses, list):
        responses = [responses]

    response_iter = iter(responses)

    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock()

    async def get_response(*args, **kwargs):
        try:
            return next(response_iter)
        except StopIteration:
            return responses[-1]  # Repeat last response

    mock.get = AsyncMock(side_effect=get_response)
    mock.options = AsyncMock(side_effect=get_response)
    mock.head = AsyncMock(side_effect=get_response)

    return mock


class TestCorsCheckInit:
    """Tests for CorsCheck initialization."""

    def test_default_initialization(self):
        """Check initializes with defaults."""
        check = CorsCheck()

        assert check.name == "cors"
        assert "https://evil.attacker.com" in check.TEST_ORIGINS
        assert "null" in check.TEST_ORIGINS


class TestCorsCheckService:
    """Tests for CorsCheck.check_service."""

    async def test_cors_wildcard_detection(self, sample_service):
        """CORS wildcard origin creates observation."""
        check = CorsCheck()
        check.TEST_ORIGINS = ["https://evil.com"]

        response = make_response(
            headers={
                "access-control-allow-origin": "*",
            }
        )

        with patch("app.checks.web.cors.check.AsyncHttpClient", return_value=mock_client(response)):
            result = await check.check_service(sample_service, {})

        wildcard_observations = [f for f in result.observations if "wildcard" in f.title.lower()]
        assert len(wildcard_observations) == 1
        assert wildcard_observations[0].severity == "medium"

    async def test_cors_wildcard_with_credentials(self, sample_service):
        """Wildcard with credentials is high severity."""
        check = CorsCheck()
        check.TEST_ORIGINS = ["https://evil.com"]

        response = make_response(
            headers={
                "access-control-allow-origin": "*",
                "access-control-allow-credentials": "true",
            }
        )

        with patch("app.checks.web.cors.check.AsyncHttpClient", return_value=mock_client(response)):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 1
        assert result.observations[0].severity == "high"

    async def test_cors_origin_reflection(self, sample_service):
        """Reflected origin creates observation."""
        check = CorsCheck()
        check.TEST_ORIGINS = ["https://evil.attacker.com"]

        response = make_response(
            headers={
                "access-control-allow-origin": "https://evil.attacker.com",
            }
        )

        with patch("app.checks.web.cors.check.AsyncHttpClient", return_value=mock_client(response)):
            result = await check.check_service(sample_service, {})

        reflect_observations = [f for f in result.observations if "reflects" in f.title.lower()]
        assert len(reflect_observations) == 1

    async def test_cors_null_origin(self, sample_service):
        """Null origin creates observation."""
        check = CorsCheck()
        check.TEST_ORIGINS = ["null"]

        response = make_response(
            headers={
                "access-control-allow-origin": "null",
            }
        )

        with patch("app.checks.web.cors.check.AsyncHttpClient", return_value=mock_client(response)):
            result = await check.check_service(sample_service, {})

        null_observations = [f for f in result.observations if "null" in f.title.lower()]
        assert len(null_observations) == 1
        assert null_observations[0].severity == "medium"

    async def test_no_cors_headers(self, sample_service):
        """No CORS headers means no observation."""
        check = CorsCheck()
        check.TEST_ORIGINS = ["https://evil.com"]

        response = make_response(headers={})

        with patch("app.checks.web.cors.check.AsyncHttpClient", return_value=mock_client(response)):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 0

    async def test_error_handling(self, sample_service):
        """HTTP errors are captured."""
        check = CorsCheck()
        check.TEST_ORIGINS = ["https://evil.com"]

        response = make_response(error="Connection refused")

        with patch("app.checks.web.cors.check.AsyncHttpClient", return_value=mock_client(response)):
            result = await check.check_service(sample_service, {})

        assert len(result.errors) > 0
