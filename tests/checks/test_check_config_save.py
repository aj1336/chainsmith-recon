"""
Tests for the "save as default" config-write endpoint + folder locator (Phase 56.17).

`PUT /api/v1/checks/{name}/config` persists tunable overrides into a check's
`config.yaml` (layer 3): on_critical at top level, numeric knobs under `defaults:`,
other keys preserved, the merged doc schema-validated before writing.
"""

import uuid

import pytest
import yaml
from fastapi import HTTPException

from app.api_models import CheckOverride
from app.component_loader import find_component_dir

pytestmark = pytest.mark.unit


def _write_check(root, suite, name, config=None):
    d = root / suite / name
    d.mkdir(parents=True)
    (d / "contract.yaml").write_text(
        yaml.safe_dump(
            {
                "id": str(uuid.uuid4()),
                "name": name,
                "type": "check",
                "description": f"{name} desc",
                "entry": "check.py:Foo",
                "suite": suite,
            }
        ),
        encoding="utf-8",
    )
    (d / "check.py").write_text("class Foo:\n    pass\n", encoding="utf-8")
    if config is not None:
        (d / "config.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")
    return d


# ── find_component_dir ───────────────────────────────────────────────


def test_find_component_dir_locates_and_misses(tmp_path):
    _write_check(tmp_path, "web", "web_one")
    found = find_component_dir(tmp_path, "web_one")
    assert found == tmp_path / "web" / "web_one"
    assert find_component_dir(tmp_path, "nope") is None


# ── save endpoint ────────────────────────────────────────────────────


async def _save(monkeypatch, tmp_path, check_name, body):
    """Call the endpoint with _CHECKS_ROOT pointed at a synthetic tree and the
    display-cache refresh stubbed (it would re-scan the real app/checks)."""
    import app.routes.checks as checks_mod

    monkeypatch.setattr(checks_mod, "_CHECKS_ROOT", tmp_path)
    monkeypatch.setattr(checks_mod, "rebuild_available_checks", lambda: {})
    return await checks_mod.save_check_config_default(check_name, body)


async def test_save_writes_knobs_under_defaults_and_on_critical_top_level(monkeypatch, tmp_path):
    _write_check(tmp_path, "web", "web_one", config={"enabled": True, "reason": "keep me"})
    res = await _save(
        monkeypatch,
        tmp_path,
        "web_one",
        CheckOverride(timeout_seconds=45.0, retry_count=2, on_critical="stop"),
    )
    assert res["status"] == "saved"
    saved = yaml.safe_load((tmp_path / "web" / "web_one" / "config.yaml").read_text())
    assert saved["defaults"]["timeout_seconds"] == 45.0
    assert saved["defaults"]["retry_count"] == 2
    assert saved["on_critical"] == "stop"
    # untouched keys preserved
    assert saved["enabled"] is True
    assert saved["reason"] == "keep me"


async def test_save_merges_into_existing_defaults(monkeypatch, tmp_path):
    _write_check(
        tmp_path,
        "web",
        "web_two",
        config={"enabled": True, "defaults": {"timeout_seconds": 10.0, "retry_count": 5}},
    )
    await _save(monkeypatch, tmp_path, "web_two", CheckOverride(timeout_seconds=99.0))
    saved = yaml.safe_load((tmp_path / "web" / "web_two" / "config.yaml").read_text())
    assert saved["defaults"]["timeout_seconds"] == 99.0  # overwritten
    assert saved["defaults"]["retry_count"] == 5  # preserved


async def test_save_creates_config_when_absent(monkeypatch, tmp_path):
    _write_check(tmp_path, "web", "web_three")  # no config.yaml
    await _save(monkeypatch, tmp_path, "web_three", CheckOverride(requests_per_second=3.0))
    cfg_path = tmp_path / "web" / "web_three" / "config.yaml"
    assert cfg_path.exists()
    assert yaml.safe_load(cfg_path.read_text())["defaults"]["requests_per_second"] == 3.0


async def test_save_unknown_check_404(monkeypatch, tmp_path):
    _write_check(tmp_path, "web", "web_one")
    with pytest.raises(HTTPException) as ei:
        await _save(monkeypatch, tmp_path, "ghost", CheckOverride(timeout_seconds=5.0))
    assert ei.value.status_code == 404


async def test_save_empty_body_400(monkeypatch, tmp_path):
    _write_check(tmp_path, "web", "web_one")
    with pytest.raises(HTTPException) as ei:
        await _save(monkeypatch, tmp_path, "web_one", CheckOverride())
    assert ei.value.status_code == 400


async def test_saved_config_roundtrips_through_loader(monkeypatch, tmp_path):
    # After a save, the written config.yaml must still pass verify_contracts.
    from app.component_loader import verify_contracts

    _write_check(tmp_path, "web", "web_one", config={"enabled": True})
    await _save(
        monkeypatch, tmp_path, "web_one", CheckOverride(timeout_seconds=20.0, on_critical="stop")
    )
    violations = verify_contracts(tmp_path, "check", env={})
    assert [v for v in violations if v.code.startswith(("config-", "suite-"))] == []
