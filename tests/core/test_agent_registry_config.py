"""
Phase 56.10c — agent config migration: registry env back-compat shim + param accessor.

When the adjudicator / triage / coach / researcher knobs moved out of
ChainsmithConfig into each agent's `config.yaml`, the agent registry gained:
  - config.yaml `enabled` as the single source of truth (disabled → not discovered)
  - a legacy `CHAINSMITH_<AGENT>_*` env back-compat shim (toggles enabled /
    overrides params at discovery time)
  - `AgentRegistry.param()` to read resolved `config.yaml` parameters
  - `from_spec` forwarding ctor-applicable params (memory_cap, offline_mode)

These tests lock that behavior.
"""

from unittest.mock import MagicMock

import pytest

from app.agents.registry import _apply_legacy_env, discover_agent_specs
from app.components.config_models import ComponentConfig

pytestmark = pytest.mark.unit


class TestApplyLegacyEnv:
    """Unit tests for the legacy env back-compat shim (pure function)."""

    def test_enabled_toggle_off(self):
        cfg = ComponentConfig(enabled=True)
        out = _apply_legacy_env("adjudicator", cfg, {"CHAINSMITH_ADJUDICATOR_ENABLED": "false"})
        assert out.enabled is False

    def test_enabled_toggle_on(self):
        cfg = ComponentConfig(enabled=False)
        out = _apply_legacy_env("triage", cfg, {"CHAINSMITH_TRIAGE_ENABLED": "yes"})
        assert out.enabled is True

    def test_param_override_memory_cap(self):
        cfg = ComponentConfig(parameters={"memory_cap": 10})
        out = _apply_legacy_env("coach", cfg, {"CHAINSMITH_COACH_MEMORY_CAP": "4"})
        assert out.parameters["memory_cap"] == 4

    def test_param_override_offline_mode(self):
        cfg = ComponentConfig(parameters={"offline_mode": False})
        out = _apply_legacy_env("researcher", cfg, {"CHAINSMITH_RESEARCHER_OFFLINE": "1"})
        assert out.parameters["offline_mode"] is True

    def test_no_env_is_noop_same_object(self):
        cfg = ComponentConfig(enabled=True, parameters={"memory_cap": 10})
        assert _apply_legacy_env("coach", cfg, {}) is cfg

    def test_uncoercible_value_ignored(self):
        cfg = ComponentConfig(parameters={"memory_cap": 10})
        out = _apply_legacy_env("coach", cfg, {"CHAINSMITH_COACH_MEMORY_CAP": "not-an-int"})
        assert out.parameters["memory_cap"] == 10

    def test_unknown_agent_is_noop(self):
        cfg = ComponentConfig(enabled=True)
        # An env var keyed to a different agent must not affect this one.
        assert (
            _apply_legacy_env("verifier", cfg, {"CHAINSMITH_ADJUDICATOR_ENABLED": "false"}) is cfg
        )


class TestDiscoveryEnvShim:
    """End-to-end: env vars flow through discovery into the registry."""

    def test_disabled_via_env_not_discovered(self, monkeypatch):
        monkeypatch.setenv("CHAINSMITH_ADJUDICATOR_ENABLED", "false")
        reg = discover_agent_specs()
        assert "adjudicator" not in reg
        assert "triage" in reg  # other agents unaffected

    def test_memory_cap_env_flows_to_param_and_ctor(self, monkeypatch):
        monkeypatch.setenv("CHAINSMITH_COACH_MEMORY_CAP", "4")
        reg = discover_agent_specs()
        assert reg.param("coach", "memory_cap") == 4
        agent = reg.create("coach", client=MagicMock())
        assert agent.memory_cap == 4

    def test_researcher_offline_env_flows_to_ctor(self, monkeypatch):
        monkeypatch.setenv("CHAINSMITH_RESEARCHER_OFFLINE", "true")
        reg = discover_agent_specs()
        assert reg.param("researcher", "offline_mode") is True
        agent = reg.create("researcher", client=MagicMock())
        assert agent.offline_mode is True


class TestParamAccessor:
    """AgentRegistry.param() reads resolved config.yaml parameters."""

    def test_defaults_from_config_yaml(self):
        reg = discover_agent_specs()
        assert reg.param("adjudicator", "context_file") == "~/.chainsmith/adjudicator_context.yaml"
        assert reg.param("triage", "context_file") == "~/.chainsmith/triage_context.yaml"
        assert reg.param("triage", "kb_path") == "app/data/remediation_guidance.json"
        assert reg.param("coach", "memory_cap") == 10
        assert reg.param("researcher", "offline_mode") is False

    def test_absent_agent_returns_default(self):
        reg = discover_agent_specs()
        assert reg.param("does-not-exist", "whatever", "fallback") == "fallback"

    def test_missing_key_returns_default(self):
        reg = discover_agent_specs()
        assert reg.param("coach", "no_such_key", 99) == 99
