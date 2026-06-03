"""
Tests for app/advisors/check_proof/advisor.py

Minimal coverage (the advisor had no tests before 56.11 — gap closed here):
- Folder-shape discovery (discover_advisor_specs)
- config.yaml hydration into the typed CheckProofAdvisorConfig
- Construction with a templates dir; empty/missing dir is tolerated
- generate_batch filters to verified observations (empty in → empty out)
"""

import pytest

from app.advisors.base import BaseAdvisor
from app.advisors.check_proof.advisor import CheckProofAdvisor, CheckProofAdvisorConfig
from app.advisors.registry import discover_advisor_specs
from app.components.config_models import ComponentConfig

pytestmark = pytest.mark.unit


# ═══════════════════════════════════════════════════════════════════
# Discovery + Config Resolution
# ═══════════════════════════════════════════════════════════════════


class TestDiscoveryAndConfig:
    def test_check_proof_is_discovered(self):
        registry = discover_advisor_specs()
        assert "check_proof" in registry.names()

    def test_enabled_by_default(self):
        registry = discover_advisor_specs()
        assert registry.config("check_proof").enabled is True

    def test_entry_class_is_baseadvisor(self):
        registry = discover_advisor_specs()
        cls = registry.entry_cls("check_proof")
        assert cls is CheckProofAdvisor
        assert issubclass(cls, BaseAdvisor)

    def test_config_yaml_hydrates_typed_config(self):
        registry = discover_advisor_specs()
        cfg = CheckProofAdvisorConfig.from_component_config(registry.config("check_proof"))
        assert cfg.enabled is True
        assert cfg.trigger == "operator_selected"
        assert cfg.include_commands is True
        assert cfg.include_screenshots is True
        assert cfg.template_dir == "app/data/proof_templates/"

    def test_from_component_config_reads_parameters(self):
        comp = ComponentConfig(
            enabled=False,
            parameters={
                "trigger": "auto_verified",
                "include_commands": False,
                "include_screenshots": False,
                "template_dir": "/custom/templates/",
            },
        )
        cfg = CheckProofAdvisorConfig.from_component_config(comp)
        assert cfg.enabled is False
        assert cfg.trigger == "auto_verified"
        assert cfg.include_commands is False
        assert cfg.include_screenshots is False
        assert cfg.template_dir == "/custom/templates/"


# ═══════════════════════════════════════════════════════════════════
# Construction
# ═══════════════════════════════════════════════════════════════════


class TestConstruction:
    def test_missing_template_dir_is_tolerated(self, tmp_path):
        """A non-existent templates dir yields an empty template set, no crash."""
        advisor = CheckProofAdvisor(template_dir=tmp_path / "does_not_exist")
        assert advisor.templates == {}

    def test_empty_template_dir(self, tmp_path):
        advisor = CheckProofAdvisor(template_dir=tmp_path)
        assert advisor.templates == {}

    def test_generate_batch_empty_returns_empty(self, tmp_path):
        advisor = CheckProofAdvisor(template_dir=tmp_path)
        assert advisor.generate_batch([]) == []
