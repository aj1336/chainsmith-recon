"""
Tests for per-value config provenance + env-override helpers (Phase 56.16).

`ConfigResolver.resolve` now records which precedence layer (§5.1) won each knob
(`class_default` / `suite` / `config` / `env`) and the source of `on_critical`.
The env helpers enumerate the `CHAINSMITH__<C>__<P>` namespace for strict
validation (`detect_env_problems`) and startup/CLI surfacing
(`active_env_overrides`).
"""

import pytest

from app.components.config_models import ComponentConfig, Defaults, SuiteConfig
from app.components.config_resolver import (
    ConfigResolver,
    active_env_overrides,
    detect_env_problems,
    env_key,
)

pytestmark = pytest.mark.unit


class FakeCheck:
    timeout_seconds = 30.0
    requests_per_second = 10.0
    retry_count = 1
    delay_between_targets = 0.1


def _resolve(component_config, suite_config=None, env=None, name="fake_check"):
    return ConfigResolver(env=env or {}).resolve(name, FakeCheck, component_config, suite_config)


# ── knob provenance ──────────────────────────────────────────────────


def test_class_default_provenance_when_nothing_overrides():
    rc = _resolve(ComponentConfig())
    assert rc.timeout_seconds == 30.0
    assert all(
        rc.provenance[k] == "class_default"
        for k in ("timeout_seconds", "requests_per_second", "retry_count", "delay_between_targets")
    )


def test_suite_layer_attributed():
    suite = SuiteConfig(name="web", defaults=Defaults(timeout_seconds=15.0))
    rc = _resolve(ComponentConfig(), suite)
    assert rc.timeout_seconds == 15.0
    assert rc.provenance["timeout_seconds"] == "suite"
    assert rc.provenance["retry_count"] == "class_default"  # untouched


def test_config_layer_overrides_suite():
    suite = SuiteConfig(name="web", defaults=Defaults(timeout_seconds=15.0))
    comp = ComponentConfig(defaults=Defaults(timeout_seconds=7.0))
    rc = _resolve(comp, suite)
    assert rc.timeout_seconds == 7.0
    assert rc.provenance["timeout_seconds"] == "config"


def test_env_layer_wins_and_is_attributed():
    comp = ComponentConfig(defaults=Defaults(timeout_seconds=7.0))
    env = {env_key("fake_check", "timeout_seconds"): "99"}
    rc = _resolve(comp, env=env)
    assert rc.timeout_seconds == 99.0
    assert rc.provenance["timeout_seconds"] == "env"


def test_uncoercible_env_is_ignored_keeps_lower_layer_provenance():
    comp = ComponentConfig(defaults=Defaults(timeout_seconds=7.0))
    env = {env_key("fake_check", "timeout_seconds"): "not_a_number"}
    rc = _resolve(comp, env=env)
    assert rc.timeout_seconds == 7.0  # env ignored
    assert rc.provenance["timeout_seconds"] == "config"  # last good layer


# ── on_critical provenance ───────────────────────────────────────────


def test_on_critical_from_config():
    rc = _resolve(ComponentConfig(on_critical="stop"))
    assert rc.on_critical == "stop"
    assert rc.provenance["on_critical"] == "config"


def test_on_critical_inherit_resolves_to_suite():
    suite = SuiteConfig(name="web", on_critical="stop")
    rc = _resolve(ComponentConfig(on_critical="inherit"), suite)
    assert rc.on_critical == "stop"
    assert rc.provenance["on_critical"] == "suite"


def test_on_critical_inherit_falls_to_global_default():
    rc = _resolve(ComponentConfig(on_critical="inherit"))
    assert rc.on_critical == "annotate"
    assert rc.provenance["on_critical"] == "default"


# ── env helpers ──────────────────────────────────────────────────────


def test_env_key_construction():
    assert (
        env_key("web_robots_txt", "timeout_seconds")
        == "CHAINSMITH__WEB_ROBOTS_TXT__TIMEOUT_SECONDS"
    )


def test_detect_env_problems_flags_unknown_and_uncoercible():
    names = ["network_port_scan"]
    env = {
        env_key("network_port_scan", "timeout_seconds"): "45",  # valid
        "CHAINSMITH__NETWORK_PORT_SCAN__TIMOUT_SECONDS": "5",  # typo
        env_key("network_port_scan", "retry_count"): "abc",  # uncoercible
        "CHAINSMITH_SWARM_ENABLED": "true",  # legacy single-underscore — ignored
    }
    by_code = {code: key for key, code, _ in detect_env_problems(names, env)}
    assert by_code["env-unknown"] == "CHAINSMITH__NETWORK_PORT_SCAN__TIMOUT_SECONDS"
    assert by_code["env-uncoercible"] == env_key("network_port_scan", "retry_count")
    assert len(by_code) == 2  # the valid + legacy vars produce no problem


def test_detect_env_problems_clean_when_all_valid():
    names = ["web_robots_txt"]
    env = {env_key("web_robots_txt", "timeout_seconds"): "20"}
    assert detect_env_problems(names, env) == []


def test_active_env_overrides_lists_valid_only_sorted():
    names = ["a_check", "b_check"]
    env = {
        env_key("b_check", "retry_count"): "3",  # valid
        env_key("a_check", "timeout_seconds"): "12",  # valid
        env_key("a_check", "retry_count"): "oops",  # uncoercible — excluded
        "CHAINSMITH_LEGACY": "x",  # single underscore — excluded
    }
    assert active_env_overrides(names, env) == [
        ("a_check", "timeout_seconds", "12"),
        ("b_check", "retry_count", "3"),
    ]
