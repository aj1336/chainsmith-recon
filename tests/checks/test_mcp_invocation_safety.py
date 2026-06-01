from unittest.mock import AsyncMock

import pytest

from app.checks.base import Service
from app.checks.mcp.invocation_safety import (
    build_probe_payload,
    build_safe_payload,
    cap_response,
    classify_tool_probe_type,
    is_payload_safe,
)
from app.lib.http import HttpResponse


@pytest.fixture
def sample_service():
    return Service(
        url="http://mcp.example.com:8080",
        host="mcp.example.com",
        port=8080,
        scheme="http",
        service_type="ai",
    )


@pytest.fixture
def mcp_server_context(sample_service):
    return {
        "mcp_servers": [
            {
                "url": "http://mcp.example.com:8080/mcp",
                "path": "/mcp",
                "transport": "http",
                "capabilities": ["tools", "resources"],
                "auth_required": False,
                "server_info": {"name": "test-server", "version": "1.0"},
                "service": sample_service.to_dict(),
            }
        ]
    }


@pytest.fixture
def mcp_tools_context(mcp_server_context):
    ctx = dict(mcp_server_context)
    ctx["mcp_tools"] = [
        {
            "name": "read_file",
            "description": "Read a file from disk",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
            "risk_level": "high",
            "service_host": "mcp.example.com",
            "server_url": "http://mcp.example.com:8080/mcp",
        },
        {
            "name": "execute_command",
            "description": "Execute shell command",
            "input_schema": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
            "risk_level": "critical",
            "service_host": "mcp.example.com",
            "server_url": "http://mcp.example.com:8080/mcp",
        },
        {
            "name": "http_fetch",
            "description": "Fetch a URL",
            "input_schema": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
            "risk_level": "high",
            "service_host": "mcp.example.com",
            "server_url": "http://mcp.example.com:8080/mcp",
        },
        {
            "name": "send_email",
            "description": "Send an email message",
            "input_schema": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "body": {"type": "string"},
                },
            },
            "risk_level": "high",
            "service_host": "mcp.example.com",
            "server_url": "http://mcp.example.com:8080/mcp",
        },
        {
            "name": "get_time",
            "description": "Get current time",
            "input_schema": {},
            "risk_level": "info",
            "service_host": "mcp.example.com",
            "server_url": "http://mcp.example.com:8080/mcp",
        },
    ]
    return ctx


def make_response(status_code=200, headers=None, body="", error=None):
    return HttpResponse(
        url="http://test",
        status_code=status_code,
        headers=headers or {},
        body=body,
        elapsed_ms=10.0,
        error=error,
    )


def mock_client_factory():
    """Create a properly configured mock client with context manager."""
    mock = AsyncMock()
    mock.__aenter__ = AsyncMock(return_value=mock)
    mock.__aexit__ = AsyncMock()
    return mock


class TestInvocationSafety:
    def test_build_safe_payload(self):
        tool = {
            "input_schema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "count": {"type": "integer", "minimum": 0},
                },
                "required": ["path"],
            }
        }
        payload = build_safe_payload(tool)
        assert "path" in payload
        assert isinstance(payload["path"], str)

    def test_build_safe_payload_with_enum(self):
        tool = {
            "input_schema": {
                "properties": {"mode": {"type": "string", "enum": ["read", "write"]}},
                "required": ["mode"],
            }
        }
        payload = build_safe_payload(tool)
        assert payload.get("mode") == "read"

    def test_build_probe_payload_file(self):
        tool = {
            "name": "read_file",
            "input_schema": {"properties": {"path": {"type": "string"}}, "required": ["path"]},
        }
        payload = build_probe_payload(tool, "file")
        assert "/etc/hostname" in payload.get("path", "")

    def test_build_probe_payload_exec(self):
        tool = {
            "name": "exec",
            "input_schema": {
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        }
        payload = build_probe_payload(tool, "exec")
        assert "chainsmith-probe" in payload.get("command", "")

    def test_is_payload_safe(self):
        assert is_payload_safe({"path": "/etc/hostname"}) is True
        assert is_payload_safe({"command": "echo test"}) is True
        assert is_payload_safe({"command": "rm -rf /"}) is False
        assert is_payload_safe({"query": "DROP TABLE users"}) is False

    def test_cap_response(self):
        short = "hello"
        assert cap_response(short) == "hello"
        long_str = "x" * 2000
        capped = cap_response(long_str)
        assert len(capped) < 2000
        assert "truncated" in capped

    def test_classify_tool_probe_type(self):
        assert classify_tool_probe_type({"name": "read_file", "description": ""}) == "file"
        assert classify_tool_probe_type({"name": "http_fetch", "description": ""}) == "fetch"
        assert classify_tool_probe_type({"name": "execute_command", "description": ""}) == "exec"
        assert classify_tool_probe_type({"name": "sql_query", "description": ""}) == "search"
        assert classify_tool_probe_type({"name": "get_time", "description": ""}) == "generic"
