"""
Tests for disabled-visible component introspection (Phase 56.15).

`discover_component_metadata` surfaces ALL components (enabled AND disabled),
import-free, so the API/WebUI can offer an enable/disable toggle. Covered against
both synthetic component trees and the real app/checks tree, plus the
`/api/v1/checks?include_disabled` route logic.
"""

import uuid

import pytest
import yaml

from app.check_resolver import get_all_check_metadata, get_real_checks
from app.component_loader import discover_component_metadata

pytestmark = pytest.mark.unit


def _write_check(root, suite, name, *, enabled=True, reason="", on_critical="annotate"):
    d = root / suite / name
    d.mkdir(parents=True)
    (d / "contract.yaml").write_text(
        yaml.safe_dump(
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "type": "check",
                "description": f"{name} description",
                "entry": "check.py:Foo",
                "suite": suite,
            }
        ),
        encoding="utf-8",
    )
    cfg = {"enabled": enabled}
    if reason:
        cfg["reason"] = reason
    if on_critical != "annotate":
        cfg["on_critical"] = on_critical
    (d / "config.yaml").write_text(yaml.safe_dump(cfg), encoding="utf-8")


# ── Synthetic trees ──────────────────────────────────────────────────


def test_enabled_and_disabled_both_listed(tmp_path):
    _write_check(tmp_path, "web", "web_on")
    _write_check(tmp_path, "web", "web_off", enabled=False, reason="client prohibits")
    metas = discover_component_metadata(tmp_path, "check")
    by_name = {m.name: m for m in metas}

    assert by_name["web_on"].enabled is True
    assert by_name["web_off"].enabled is False
    assert by_name["web_off"].reason == "client prohibits"
    assert by_name["web_on"].suite == "web"
    assert by_name["web_on"].description == "web_on description"


def test_disabled_suite_disables_all_members(tmp_path):
    _write_check(tmp_path, "ai", "ai_one")
    _write_check(tmp_path, "ai", "ai_two")
    (tmp_path / "ai" / "suite.yaml").write_text(
        yaml.safe_dump({"name": "ai", "enabled": False}), encoding="utf-8"
    )
    metas = discover_component_metadata(tmp_path, "check")
    # Both members are effectively disabled even though their config.yaml enabled:true
    assert all(m.enabled is False for m in metas)


def test_on_critical_inherit_resolves_against_suite(tmp_path):
    _write_check(tmp_path, "web", "web_inh", on_critical="inherit")
    (tmp_path / "web" / "suite.yaml").write_text(
        yaml.safe_dump({"name": "web", "enabled": True, "on_critical": "stop"}), encoding="utf-8"
    )
    meta = discover_component_metadata(tmp_path, "check")[0]
    assert meta.on_critical == "stop"  # inherit → suite value


def test_malformed_contract_is_skipped_not_raised(tmp_path):
    _write_check(tmp_path, "web", "web_ok")
    bad = tmp_path / "web" / "web_bad"
    bad.mkdir(parents=True)
    (bad / "contract.yaml").write_text("id: not-a-uuid\nname: web_bad\n", encoding="utf-8")
    metas = discover_component_metadata(tmp_path, "check")
    names = {m.name for m in metas}
    assert "web_ok" in names
    assert "web_bad" not in names  # malformed → omitted for display


def test_empty_root_returns_empty(tmp_path):
    assert discover_component_metadata(tmp_path / "nope", "check") == []


# ── Real app/checks tree ─────────────────────────────────────────────


def test_real_tree_enabled_matches_loader():
    metas = get_all_check_metadata()
    enabled_meta = {m.name for m in metas if m.enabled}
    loaded = {c.name for c in get_real_checks()}
    # The loader builds exactly the enabled components.
    assert enabled_meta == loaded


def test_real_tree_has_disabled_checks():
    metas = get_all_check_metadata()
    disabled = [m for m in metas if not m.enabled]
    # Phase 56.4 left several AI checks dormant (enabled:false).
    assert disabled, "expected at least one disabled check in the tree"
    assert all(m.enabled is False for m in disabled)
    assert {m.name for m in disabled}.isdisjoint({c.name for c in get_real_checks()})


# ── Route: /api/v1/checks?include_disabled ───────────────────────────


async def test_route_excludes_disabled_by_default():
    from app.routes.checks import get_available_checks

    result = await get_available_checks(include_disabled=False)
    assert all("enabled" not in c or c["enabled"] for c in result["checks"])


async def test_route_includes_disabled_when_requested():
    from app.routes.checks import get_available_checks

    result = await get_available_checks(include_disabled=True)
    by_enabled = [c for c in result["checks"] if c.get("enabled")]
    disabled = [c for c in result["checks"] if c.get("enabled") is False]
    assert by_enabled and disabled  # both present
    # disabled entries carry the shape the WebUI grid needs
    sample = disabled[0]
    assert {"name", "suite", "enabled", "reason", "on_critical"} <= sample.keys()
