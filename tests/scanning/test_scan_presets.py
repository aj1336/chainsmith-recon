"""
Tests for app/scan_presets.py - scan presets (Phase 56.14 / phase-17 Wave 3).

Covers the fallback-first loader, Preset validation, the §5.1 layer-6 selection
precedence (explicit beats preset), and the scan-time runtime layer (intrusive
filter + per-check knob overrides). Plus a byte-equivalence guard that the shipped
app/data/presets.yaml resolves to the same presets as the in-code fallback.
"""

import pytest

from app.lib import datafiles
from app.scan_presets import (
    _FALLBACK_PRESETS,
    Preset,
    apply_runtime,
    get_preset,
    list_presets,
    preset_names,
    resolve_selection,
)

pytestmark = pytest.mark.unit


class _DummyCheck:
    """Minimal stand-in carrying the attributes apply_runtime touches."""

    def __init__(self, name: str, intrusive: bool = False):
        self.name = name
        self.intrusive = intrusive
        self.timeout_seconds = 30.0
        self.requests_per_second = 10.0
        self.retry_count = 1
        self.delay_between_targets = 0.1
        self.on_critical = "annotate"


# ── Shipped presets parse, validate, and match the fallback ──────────


def test_shipped_presets_file_exists():
    assert (datafiles.DATA_ROOT / "presets.yaml").exists()


def test_all_four_presets_present():
    assert set(preset_names()) == {"quick", "thorough", "passive", "ai-focused"}


def test_shipped_presets_match_fallback():
    """The data file must resolve to the same validated presets as the inline
    fallback (behavior-preserving externalization, like 56.13)."""
    shipped = {name: get_preset(name) for name in preset_names()}
    fallback = {name: Preset(**raw) for name, raw in _FALLBACK_PRESETS.items()}
    assert shipped == fallback


def test_list_presets_returns_descriptions():
    listed = list_presets()
    assert set(listed) == {"quick", "thorough", "passive", "ai-focused"}
    assert all(desc for desc in listed.values())


def test_quick_preset_fields():
    p = get_preset("quick")
    assert p.suites == ["network", "web"]
    assert p.port_profile == "web"
    assert p.defaults.retry_count == 1
    assert p.intrusive is None


def test_passive_preset_fields():
    p = get_preset("passive")
    assert p.intrusive is False
    assert p.defaults.requests_per_second == 5.0
    assert p.suites is None


def test_ai_focused_preset_fields():
    p = get_preset("ai-focused")
    assert p.suites == ["ai", "agent", "rag", "cag", "mcp"]
    assert p.port_profile is None


def test_unknown_preset_returns_none():
    assert get_preset("nope") is None


# ── Preset validation ────────────────────────────────────────────────


def test_unknown_suite_rejected():
    with pytest.raises(ValueError, match="unknown suite"):
        Preset(suites=["web", "bogus"])


def test_unknown_port_profile_rejected():
    with pytest.raises(ValueError, match="unknown port_profile"):
        Preset(port_profile="turbo")


def test_unknown_on_critical_rejected():
    with pytest.raises(ValueError, match="on_critical"):
        Preset(on_critical="explode")


def test_inherit_on_critical_rejected():
    # "inherit" is meaningless at scan time — only concrete values allowed.
    with pytest.raises(ValueError):
        Preset(on_critical="inherit")


def test_extra_field_forbidden():
    with pytest.raises(ValueError):
        Preset(bogus_field=1)


# ── Selection precedence (§5.1 layer 6b > 6a) ────────────────────────


def test_explicit_suites_beat_preset():
    p = get_preset("quick")  # suites=[network, web], port_profile=web
    suites, checks, pp = resolve_selection(p, suites=["ai"], checks=None, port_profile=None)
    assert suites == ["ai"]  # explicit wins
    assert pp == "web"  # preset's port_profile still inherited (not overridden)


def test_explicit_port_profile_beats_preset():
    p = get_preset("quick")
    _, _, pp = resolve_selection(p, suites=None, checks=None, port_profile="full")
    assert pp == "full"


def test_preset_used_when_no_explicit():
    p = get_preset("quick")
    suites, checks, pp = resolve_selection(p, suites=None, checks=None, port_profile=None)
    assert suites == ["network", "web"]
    assert pp == "web"


def test_no_preset_returns_explicit():
    suites, checks, pp = resolve_selection(
        None, suites=["web"], checks=["web_cors"], port_profile="ai"
    )
    assert suites == ["web"]
    assert checks == ["web_cors"]
    assert pp == "ai"


def test_no_preset_no_explicit_is_all_none():
    assert resolve_selection(None, suites=None, checks=None, port_profile=None) == (
        None,
        None,
        None,
    )


# ── Runtime layer: intrusive filter + knob overrides ─────────────────


def test_apply_runtime_none_preset_is_noop():
    checks = [_DummyCheck("a"), _DummyCheck("b", intrusive=True)]
    assert apply_runtime(None, checks) is checks


def test_passive_filters_out_intrusive_checks():
    checks = [
        _DummyCheck("web_robots_txt", intrusive=False),
        _DummyCheck("web_xss", intrusive=True),
    ]
    result = apply_runtime(get_preset("passive"), checks)
    assert [c.name for c in result] == ["web_robots_txt"]
    # passive also lowers the request rate on survivors
    assert result[0].requests_per_second == 5.0


def test_thorough_overrides_retry_count_on_all_checks():
    checks = [_DummyCheck("a"), _DummyCheck("b")]
    result = apply_runtime(get_preset("thorough"), checks)
    assert all(c.retry_count == 2 for c in result)


def test_on_critical_override_applied():
    checks = [_DummyCheck("a")]
    apply_runtime(Preset(on_critical="stop"), checks)
    assert checks[0].on_critical == "stop"


def test_unset_knobs_are_untouched():
    """A preset that only sets retry_count must not clobber other knobs."""
    chk = _DummyCheck("a")
    chk.timeout_seconds = 99.0
    apply_runtime(Preset(defaults={"retry_count": 7}), [chk])
    assert chk.retry_count == 7
    assert chk.timeout_seconds == 99.0  # untouched


# ── Fallback-first behavior (synthetic empty DATA_ROOT) ──────────────


def test_missing_file_degrades_to_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(datafiles, "DATA_ROOT", tmp_path)
    assert set(preset_names()) == set(_FALLBACK_PRESETS)
    p = get_preset("quick")
    assert p.suites == ["network", "web"]
