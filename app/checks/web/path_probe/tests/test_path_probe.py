"""Co-located tests (Phase 56 §3) — split from test_web.py."""

from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.web.path_probe import PathProbeCheck
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


class TestPathProbeCheckInit:
    """Tests for PathProbeCheck initialization."""

    def test_default_initialization(self):
        """Check initializes with defaults."""
        check = PathProbeCheck()

        assert check.name == "path_probe"
        assert len(check.COMMON_PATHS) > 0
        assert "/admin" in check.COMMON_PATHS

    def test_severity_patterns_defined(self):
        """Severity patterns are defined."""
        check = PathProbeCheck()

        assert len(check.HIGH_SEVERITY_PATTERNS) > 0
        assert len(check.MEDIUM_SEVERITY_PATTERNS) > 0


class TestPathProbeCheckService:
    """Tests for PathProbeCheck.check_service."""

    async def test_accessible_path_creates_observation(self, sample_service):
        """HTTP 200 creates accessible path observation."""
        check = PathProbeCheck()
        check.COMMON_PATHS = ["/test"]  # Simplify for test

        response = make_response(
            status_code=200,
            headers={"content-type": "text/html"},
        )

        with patch(
            "app.checks.web.path_probe.check.AsyncHttpClient", return_value=mock_client(response)
        ):
            result = await check.check_service(sample_service, {})

        accessible_observations = [f for f in result.observations if "Accessible" in f.title]
        assert len(accessible_observations) == 1

    async def test_high_severity_paths(self, sample_service):
        """Sensitive paths get high severity."""
        check = PathProbeCheck()
        check.COMMON_PATHS = ["/.env"]

        response = make_response(
            status_code=200,
            headers={"content-type": "text/plain"},
        )

        with patch(
            "app.checks.web.path_probe.check.AsyncHttpClient", return_value=mock_client(response)
        ):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 1
        assert result.observations[0].severity == "high"

    async def test_medium_severity_paths(self, sample_service):
        """Admin paths get medium severity."""
        check = PathProbeCheck()
        check.COMMON_PATHS = ["/admin"]

        response = make_response(
            status_code=200,
            headers={"content-type": "text/html"},
        )

        with patch(
            "app.checks.web.path_probe.check.AsyncHttpClient", return_value=mock_client(response)
        ):
            result = await check.check_service(sample_service, {})

        assert len(result.observations) == 1
        assert result.observations[0].severity == "medium"

    async def test_forbidden_path_observation(self, sample_service):
        """HTTP 403 on sensitive paths creates observation."""
        check = PathProbeCheck()
        check.COMMON_PATHS = ["/admin"]

        response = make_response(status_code=403)

        with patch(
            "app.checks.web.path_probe.check.AsyncHttpClient", return_value=mock_client(response)
        ):
            result = await check.check_service(sample_service, {})

        forbidden_observations = [f for f in result.observations if "Protected" in f.title]
        assert len(forbidden_observations) == 1

    async def test_redirect_creates_observation(self, sample_service):
        """Redirects create observations."""
        check = PathProbeCheck()
        check.COMMON_PATHS = ["/admin"]

        response = make_response(
            status_code=302,
            headers={"location": "/login"},
        )

        with patch(
            "app.checks.web.path_probe.check.AsyncHttpClient", return_value=mock_client(response)
        ):
            result = await check.check_service(sample_service, {})

        redirect_observations = [f for f in result.observations if "Redirect" in f.title]
        assert len(redirect_observations) == 1

    async def test_sets_outputs(self, sample_service):
        """Outputs contain discovered paths."""
        check = PathProbeCheck()
        check.COMMON_PATHS = ["/found", "/forbidden"]

        responses = [
            make_response(status_code=200),
            make_response(status_code=403),
        ]

        with patch("app.checks.web.path_probe.check.AsyncHttpClient") as mock_cls:
            m = AsyncMock()
            m.__aenter__ = AsyncMock(return_value=m)
            m.__aexit__ = AsyncMock()
            response_iter = iter(responses)
            m.get = AsyncMock(side_effect=lambda *a, **k: next(response_iter, responses[-1]))
            mock_cls.return_value = m

            result = await check.check_service(sample_service, {})

        key = f"paths_{sample_service.port}"
        assert key in result.outputs
