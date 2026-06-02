"""
Tests for operator-context file loading.

Exercises app.engine.adjudication.load_operator_context (an engine helper, not
the adjudicator agent itself — the agent's behavior tests are co-located at
app/agents/adjudicator/tests/test_adjudicator.py).
"""

import pytest

from app.engine.adjudication import load_operator_context

pytestmark = pytest.mark.unit


class TestOperatorContextLoading:
    def test_missing_file_returns_none(self):
        result = load_operator_context(context_file="/nonexistent/path.yaml")
        assert result is None

    def test_malformed_yaml_returns_none(self, tmp_path):
        ctx_file = tmp_path / "context.yaml"
        ctx_file.write_text("just a plain string")
        result = load_operator_context(context_file=str(ctx_file))
        assert result is None

    def test_valid_file_loads(self, tmp_path):
        ctx_file = tmp_path / "context.yaml"
        ctx_file.write_text(
            "assets:\n"
            "  - domain: api.example.com\n"
            "    exposure: internet-facing\n"
            "    criticality: high\n"
            "defaults:\n"
            "  exposure: unknown\n"
            "  criticality: medium\n"
        )

        result = load_operator_context(context_file=str(ctx_file))
        assert result is not None
        assert len(result.assets) == 1
        assert result.assets[0].domain == "api.example.com"
