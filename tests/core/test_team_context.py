"""
Tests for triage team-context file loading/saving (engine layer).

These exercise app.engine.triage.load_team_context / save_team_context — the
YAML persistence helpers that read/write ~/.chainsmith/triage_context.yaml.
They are engine-only (no TriageAgent involved), so they live here rather than
co-located with the triage agent component (Phase 56.10 split).
"""

from datetime import UTC, datetime

import pytest

from app.engine.triage import load_team_context, save_team_context
from app.models import TeamContext

pytestmark = pytest.mark.unit


class TestTeamContextLoadSave:
    """Test team context YAML loading and saving."""

    def test_load_missing_file(self, tmp_path):
        """Returns None when file doesn't exist."""
        result = load_team_context(context_file=str(tmp_path / "nonexistent.yaml"))
        assert result is None

    def test_load_valid_file(self, tmp_path):
        """Loads valid YAML correctly."""
        yaml_content = (
            "deployment_velocity: yes\n"
            "incident_response: partially\n"
            "remediation_surface: app_only\n"
            "team_size: 2_to_3\n"
            'off_limits: "Auth service"\n'
            'answered_at: "2026-04-09T14:30:00Z"\n'
        )
        yaml_file = tmp_path / "triage_context.yaml"
        yaml_file.write_text(yaml_content)

        result = load_team_context(context_file=str(yaml_file))

        assert result is not None
        assert result.deployment_velocity == "yes"
        assert result.incident_response == "partially"
        assert result.remediation_surface == "app_only"
        assert result.team_size == "2_to_3"
        assert result.off_limits == "Auth service"
        assert result.answered_at is not None

    def test_load_partial_file(self, tmp_path):
        """Loads partial YAML — missing fields are None."""
        yaml_content = "deployment_velocity: no\n"
        yaml_file = tmp_path / "triage_context.yaml"
        yaml_file.write_text(yaml_content)

        result = load_team_context(context_file=str(yaml_file))

        assert result is not None
        assert result.deployment_velocity == "no"
        assert result.incident_response is None

    def test_load_malformed_file(self, tmp_path):
        """Returns None for non-mapping YAML."""
        yaml_file = tmp_path / "triage_context.yaml"
        yaml_file.write_text("- just\n- a\n- list\n")

        result = load_team_context(context_file=str(yaml_file))
        assert result is None

    def test_save_and_reload(self, tmp_path):
        """Round-trip: save then load."""
        ctx = TeamContext(
            deployment_velocity="with_approval",
            incident_response="yes",
            remediation_surface="both",
            team_size="4_plus",
            off_limits="Production DB",
            answered_at=datetime(2026, 4, 9, 14, 30, tzinfo=UTC),
        )

        yaml_file = tmp_path / "triage_context.yaml"

        assert save_team_context(ctx, context_file=str(yaml_file)) is True
        assert yaml_file.exists()

        loaded = load_team_context(context_file=str(yaml_file))
        assert loaded is not None
        assert loaded.deployment_velocity == "with_approval"
        assert loaded.team_size == "4_plus"
        assert loaded.off_limits == "Production DB"
