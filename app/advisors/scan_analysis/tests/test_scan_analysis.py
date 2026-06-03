"""
Tests for app/advisors/scan_analysis/advisor.py

Covers:
- Folder-shape discovery + config resolution (discover_advisor_specs)
- ScanAnalysisRecommendation dataclass
- ScanAnalysisAdvisorConfig defaults + config.yaml hydration
- Gap analysis: detects checks blocked by missing context
- Partial results: flags failed and skipped checks
- Follow-up suggestions: triggers based on observations
- Coverage cross-reference: detects suites with low/no coverage
- Deduplication of recommendations
- Disabled advisor returns empty list
"""

import pytest

from app.advisors.base import BaseAdvisor
from app.advisors.registry import discover_advisor_specs
from app.advisors.scan_analysis.advisor import (
    ScanAnalysisAdvisor,
    ScanAnalysisAdvisorConfig,
    ScanAnalysisRecommendation,
)
from app.components.config_models import ComponentConfig

pytestmark = pytest.mark.unit

# ── Helpers ──────────────────────────────────────────────────────


def _make_advisor(
    completed=None,
    failed=None,
    skipped=None,
    all_check_names=None,
    context=None,
    observations=None,
    check_metadata=None,
    enabled=True,
) -> ScanAnalysisAdvisor:
    """Build a ScanAnalysisAdvisor with sensible defaults for testing."""
    return ScanAnalysisAdvisor(
        completed=completed or set(),
        failed=failed or set(),
        skipped=skipped or set(),
        all_check_names=all_check_names or set(),
        context=context or {},
        observations=observations or [],
        check_metadata=check_metadata or {},
        config=ScanAnalysisAdvisorConfig(enabled=enabled),
    )


# ═══════════════════════════════════════════════════════════════════
# Discovery + Config Resolution
# ═══════════════════════════════════════════════════════════════════


class TestDiscoveryAndConfig:
    def test_scan_analysis_is_discovered(self):
        registry = discover_advisor_specs()
        assert "scan_analysis" in registry.names()

    def test_disabled_advisor_still_discovered(self):
        """Advisors are config/discovery accessors — disabled ones stay readable
        (unlike agents, which are skipped). scan_analysis ships disabled."""
        registry = discover_advisor_specs()
        assert "scan_analysis" in registry
        assert registry.config("scan_analysis").enabled is False

    def test_entry_class_is_baseadvisor(self):
        registry = discover_advisor_specs()
        cls = registry.entry_cls("scan_analysis")
        assert cls is ScanAnalysisAdvisor
        assert issubclass(cls, BaseAdvisor)

    def test_config_yaml_hydrates_typed_config(self):
        registry = discover_advisor_specs()
        cfg = ScanAnalysisAdvisorConfig.from_component_config(registry.config("scan_analysis"))
        assert cfg.enabled is False
        assert cfg.mode == "post_scan"
        assert cfg.auto_seed_urls is False
        assert cfg.require_approval is True

    def test_from_component_config_reads_parameters(self):
        comp = ComponentConfig(
            enabled=True,
            parameters={
                "mode": "between_iterations",
                "auto_seed_urls": True,
                "require_approval": False,
            },
        )
        cfg = ScanAnalysisAdvisorConfig.from_component_config(comp)
        assert cfg.enabled is True
        assert cfg.mode == "between_iterations"
        assert cfg.auto_seed_urls is True
        assert cfg.require_approval is False


# ═══════════════════════════════════════════════════════════════════
# Recommendation Dataclass
# ═══════════════════════════════════════════════════════════════════


class TestScanAnalysisRecommendation:
    def test_defaults(self):
        rec = ScanAnalysisRecommendation(check_name="foo", reason="bar")
        assert rec.confidence == "medium"
        assert rec.category == "gap_analysis"
        assert rec.context_injection == {}

    def test_to_dict(self):
        rec = ScanAnalysisRecommendation(
            check_name="test_check",
            reason="test reason",
            confidence="high",
            category="config_suggestion",
        )
        d = rec.to_dict()
        assert d["check_name"] == "test_check"
        assert d["reason"] == "test reason"
        assert d["confidence"] == "high"
        assert d["category"] == "config_suggestion"


# ═══════════════════════════════════════════════════════════════════
# Disabled Advisor
# ═══════════════════════════════════════════════════════════════════


class TestDisabledAdvisor:
    def test_returns_empty_when_disabled(self):
        advisor = _make_advisor(enabled=False)
        assert advisor.analyze() == []


# ═══════════════════════════════════════════════════════════════════
# Gap Analysis
# ═══════════════════════════════════════════════════════════════════


class TestGapAnalysis:
    def test_detects_checks_blocked_by_missing_context(self):
        """Checks that never ran due to unmet conditions are flagged."""
        advisor = _make_advisor(
            completed={"network_dns_enumeration"},
            all_check_names={"network_dns_enumeration", "network_port_scan"},
            context={"scope_domains": ["example.com"]},
            check_metadata={
                "network_port_scan": {
                    "conditions": ["target_hosts truthy"],
                    "produces": ["services"],
                },
            },
        )
        recs = advisor.analyze()
        gap_recs = [
            r for r in recs if r.category == "gap_analysis" and r.check_name == "network_port_scan"
        ]
        assert len(gap_recs) == 1
        assert "target_hosts" in gap_recs[0].reason

    def test_no_gap_when_check_ran(self):
        """Checks that completed should not appear in gap analysis."""
        advisor = _make_advisor(
            completed={"network_dns_enumeration", "network_port_scan"},
            all_check_names={"network_dns_enumeration", "network_port_scan"},
            context={"target_hosts": ["1.2.3.4"], "services": []},
            check_metadata={
                "network_port_scan": {
                    "conditions": ["target_hosts truthy"],
                    "produces": ["services"],
                },
            },
        )
        recs = advisor.analyze()
        gap_recs = [
            r for r in recs if r.check_name == "network_port_scan" and r.category == "gap_analysis"
        ]
        assert len(gap_recs) == 0

    def test_no_gap_when_context_satisfied(self):
        """Checks with satisfied conditions but that never ran for other reasons
        should still show up (they were in never_ran)."""
        advisor = _make_advisor(
            completed=set(),
            all_check_names={"network_port_scan"},
            context={"target_hosts": ["1.2.3.4"]},
            check_metadata={
                "network_port_scan": {
                    "conditions": ["target_hosts truthy"],
                    "produces": ["services"],
                },
            },
        )
        recs = advisor.analyze()
        # port_scan never ran but context IS satisfied — no missing keys
        gap_recs = [
            r for r in recs if r.check_name == "network_port_scan" and r.category == "gap_analysis"
        ]
        assert len(gap_recs) == 0


# ═══════════════════════════════════════════════════════════════════
# Partial Results
# ═══════════════════════════════════════════════════════════════════


class TestPartialResults:
    def test_flags_failed_checks(self):
        advisor = _make_advisor(
            failed={"network_service_probe"},
            all_check_names={"network_service_probe"},
            check_metadata={"network_service_probe": {"conditions": [], "produces": []}},
        )
        recs = advisor.analyze()
        failed_recs = [r for r in recs if r.check_name == "network_service_probe"]
        assert len(failed_recs) == 1
        assert "failed" in failed_recs[0].reason.lower()

    def test_flags_skipped_checks(self):
        advisor = _make_advisor(
            skipped={"web_header_analysis"},
            all_check_names={"web_header_analysis"},
            check_metadata={"web_header_analysis": {"conditions": [], "produces": []}},
        )
        recs = advisor.analyze()
        skipped_recs = [r for r in recs if r.check_name == "web_header_analysis"]
        assert len(skipped_recs) == 1
        assert "skipped" in skipped_recs[0].reason.lower()


# ═══════════════════════════════════════════════════════════════════
# Follow-Up Suggestions
# ═══════════════════════════════════════════════════════════════════


class TestFollowUpSuggestions:
    def test_suggests_followup_when_trigger_has_observations(self):
        """When llm_endpoint_discovery has observations and prompt_leakage didn't run."""
        advisor = _make_advisor(
            completed={"ai_llm_endpoint_discovery"},
            all_check_names={"ai_llm_endpoint_discovery", "ai_prompt_leakage"},
            observations=[{"check_name": "ai_llm_endpoint_discovery", "title": "Found LLM"}],
            check_metadata={
                "ai_prompt_leakage": {"conditions": ["chat_endpoints truthy"], "produces": []},
            },
        )
        recs = advisor.analyze()
        followup_recs = [r for r in recs if r.check_name == "ai_prompt_leakage"]
        assert len(followup_recs) >= 1

    def test_no_followup_when_already_ran(self):
        """Don't suggest a check that already ran."""
        advisor = _make_advisor(
            completed={"ai_llm_endpoint_discovery", "ai_prompt_leakage"},
            all_check_names={"ai_llm_endpoint_discovery", "ai_prompt_leakage"},
            observations=[{"check_name": "ai_llm_endpoint_discovery", "title": "Found LLM"}],
            check_metadata={},
        )
        recs = advisor.analyze()
        followup_recs = [r for r in recs if r.check_name == "ai_prompt_leakage"]
        assert len(followup_recs) == 0

    def test_no_followup_when_trigger_has_no_observations(self):
        """Don't suggest follow-ups for checks that produced no observations."""
        advisor = _make_advisor(
            completed={"ai_llm_endpoint_discovery"},
            all_check_names={"ai_llm_endpoint_discovery", "ai_prompt_leakage"},
            observations=[],  # no observations
            check_metadata={
                "ai_prompt_leakage": {"conditions": ["chat_endpoints truthy"], "produces": []},
            },
        )
        recs = advisor.analyze()
        followup_recs = [r for r in recs if r.check_name == "ai_prompt_leakage"]
        # May still appear from gap_analysis but NOT from follow-up
        for r in followup_recs:
            assert r.category != "follow_up"


# ═══════════════════════════════════════════════════════════════════
# Coverage Cross-Reference
# ═══════════════════════════════════════════════════════════════════


class TestCoverageCrossReference:
    def test_flags_suite_with_zero_coverage(self):
        """A suite with available checks but none ran gets flagged."""
        advisor = _make_advisor(
            completed={"network_dns_enumeration"},
            all_check_names={"network_dns_enumeration", "ai_llm_endpoint_discovery"},
            check_metadata={},
        )
        recs = advisor.analyze()
        coverage_recs = [r for r in recs if r.category == "config_suggestion"]
        # ai suite has 0 coverage (llm_endpoint_discovery is AI)
        ai_recs = [r for r in coverage_recs if "ai" in r.reason.lower()]
        assert len(ai_recs) >= 1

    def test_no_flag_when_suite_has_coverage(self):
        """A suite with sufficient coverage is not flagged."""
        # Run enough network checks to exceed threshold (3)
        advisor = _make_advisor(
            completed={
                "network_dns_enumeration",
                "network_port_scan",
                "network_tls_analysis",
                "network_service_probe",
            },
            all_check_names={
                "network_dns_enumeration",
                "network_port_scan",
                "network_tls_analysis",
                "network_service_probe",
            },
            check_metadata={},
        )
        recs = advisor.analyze()
        coverage_recs = [
            r for r in recs if r.category == "config_suggestion" and "network" in r.reason.lower()
        ]
        assert len(coverage_recs) == 0


# ═══════════════════════════════════════════════════════════════════
# Malformed / Missing Metadata
# ═══════════════════════════════════════════════════════════════════


class TestMalformedMetadata:
    def test_missing_conditions_key_does_not_crash(self):
        """check_metadata with missing 'conditions' key should not raise."""
        advisor = _make_advisor(
            completed=set(),
            all_check_names={"bad_check"},
            check_metadata={"bad_check": {"produces": ["stuff"]}},
        )
        recs = advisor.analyze()
        # Should not crash; bad_check may or may not produce a recommendation
        assert isinstance(recs, list)

    def test_empty_metadata_dict_does_not_crash(self):
        """An empty metadata dict for a check should not raise."""
        advisor = _make_advisor(
            completed=set(),
            all_check_names={"empty_meta"},
            check_metadata={"empty_meta": {}},
        )
        recs = advisor.analyze()
        assert isinstance(recs, list)

    def test_none_conditions_does_not_crash(self):
        """conditions=None should be handled gracefully."""
        advisor = _make_advisor(
            completed=set(),
            all_check_names={"null_cond"},
            check_metadata={"null_cond": {"conditions": None, "produces": []}},
        )
        recs = advisor.analyze()
        assert isinstance(recs, list)


# ═══════════════════════════════════════════════════════════════════
# Deduplication
# ═══════════════════════════════════════════════════════════════════


class TestDeduplication:
    def test_deduplicates_by_check_name(self):
        """If multiple rules produce recommendations for the same check, keep first."""
        advisor = _make_advisor(
            completed=set(),
            failed={"ai_prompt_leakage"},
            all_check_names={"ai_llm_endpoint_discovery", "ai_prompt_leakage"},
            observations=[{"check_name": "ai_llm_endpoint_discovery", "title": "Found LLM"}],
            check_metadata={
                "ai_prompt_leakage": {"conditions": ["chat_endpoints truthy"], "produces": []},
            },
        )
        recs = advisor.analyze()
        prompt_recs = [r for r in recs if r.check_name == "ai_prompt_leakage"]
        # Should be exactly 1 after dedup
        assert len(prompt_recs) == 1
