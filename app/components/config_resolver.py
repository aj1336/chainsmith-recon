"""
app/components/config_resolver.py - Load-time config precedence (Phase 56 §5.1).

Resolves the load-time baseline (layers 1-4) for a component into a
`ResolvedConfig`. Scan-time overrides (layer 6: presets / CLI / API / WebUI)
are applied later in the scan path and are NOT this resolver's concern.

Precedence, general → specific, last wins:
  1. Hardcoded class default      (the entry class's attribute values)
  2. Suite-level defaults         (suite.yaml)
  3. config.yaml defaults         (per-component — more specific than the suite)
  4. Env var                      CHAINSMITH__<COMPONENT>__<PARAM>  (ambient)

We use Pydantic for the per-source *models/validation* (contracts.py /
config_models.py) but a thin explicit resolver for the *layering*, because the
two-stage split and construct-by-key env diverge from pydantic-settings'
out-of-the-box behavior (§5.1 / §5.3). The user-override file (layer 5) is
future; scan-time (layer 6) lands in 56.14/56.17.

Env resolution is **by construction, not by parsing** (§5.1): for each known
(component, param) we build the expected key and look it up. We never
reverse-parse arbitrary CHAINSMITH_* vars, which sidesteps the `__`
split-ambiguity entirely.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Iterable, Mapping

from app.components.config_models import (
    DEFAULT_ON_CRITICAL,
    ComponentConfig,
    Defaults,
    ResolvedConfig,
    SuiteConfig,
)

logger = logging.getLogger(__name__)

# The standard tunable knobs and the type each env value is coerced to (§8.2).
_KNOBS: dict[str, type] = {
    "timeout_seconds": float,
    "requests_per_second": float,
    "retry_count": int,
    "delay_between_targets": float,
}

ENV_PREFIX = "CHAINSMITH"
ENV_DELIM = "__"  # double underscore (§5.1); single underscores stay literal in names


def env_key(component_name: str, param: str) -> str:
    """Construct the env var key for a (component, param) pair (§5.1)."""
    return f"{ENV_PREFIX}{ENV_DELIM}{component_name.upper()}{ENV_DELIM}{param.upper()}"


# The double-underscore namespace prefix that distinguishes per-component override
# vars (`CHAINSMITH__<C>__<P>`) from the legacy single-underscore `ChainsmithConfig`
# vars (`CHAINSMITH_SWARM_ENABLED`). A single-underscore var never starts with this.
ENV_OVERRIDE_PREFIX = f"{ENV_PREFIX}{ENV_DELIM}"  # "CHAINSMITH__"


def detect_env_problems(
    component_names: Iterable[str], env: Mapping[str, str]
) -> list[tuple[str, str, str]]:
    """Find malformed per-component env overrides (Phase 56.16, strict validation).

    Scans the `CHAINSMITH__*` namespace and returns `(env_key, code, message)` for
    each var that either (a) matches no known (component, knob) pair — a typo or a
    var aimed at a component type that doesn't read these knobs (`env-unknown`), or
    (b) names a real pair but carries a value that won't coerce to the knob's type
    (`env-uncoercible`). The resolver itself resolves by *construction* (never by
    scanning), so these footguns are otherwise silent; this is the one place the
    namespace is enumerated, and only for validation/surfacing.
    """
    valid: dict[str, tuple[str, str]] = {
        env_key(name, param): (name, param) for name in component_names for param in _KNOBS
    }
    problems: list[tuple[str, str, str]] = []
    for key, raw in env.items():
        if not key.startswith(ENV_OVERRIDE_PREFIX):
            continue
        pair = valid.get(key)
        if pair is None:
            problems.append(
                (key, "env-unknown", f"{key} matches no (check, knob) pair — typo or unread target")
            )
            continue
        caster = _KNOBS[pair[1]]
        try:
            caster(raw)
        except (TypeError, ValueError):
            problems.append(
                (key, "env-uncoercible", f"{key}={raw!r} is not coercible to {caster.__name__}")
            )
    return problems


def active_env_overrides(
    component_names: Iterable[str], env: Mapping[str, str]
) -> list[tuple[str, str, str]]:
    """List the valid, coercible per-component env overrides currently in effect.

    Returns `(component, param, raw_value)` for each `CHAINSMITH__<C>__<P>` var that
    names a known pair and coerces cleanly — i.e. the overrides that actually win at
    layer 4. Used for the startup log summary + `dev show-config` (Phase 56.16).
    Sorted for deterministic output.
    """
    active: list[tuple[str, str, str]] = []
    for name in component_names:
        for param, caster in _KNOBS.items():
            key = env_key(name, param)
            if key not in env:
                continue
            try:
                caster(env[key])
            except (TypeError, ValueError):
                continue  # malformed — reported by detect_env_problems, not "active"
            active.append((name, param, env[key]))
    active.sort()
    return active


class ConfigResolver:
    """Merges the load-time config layers (§5.1) into a `ResolvedConfig`."""

    def __init__(self, env: Mapping[str, str] | None = None):
        # Default to the live environment; injectable for tests.
        self._env: Mapping[str, str] = os.environ if env is None else env

    def resolve(
        self,
        component_name: str,
        entry_cls: type,
        component_config: ComponentConfig,
        suite_config: SuiteConfig | None = None,
    ) -> ResolvedConfig:
        """Resolve the load-time baseline for a single component."""
        # `provenance` records which layer last wrote each knob (§5.1) — surfaced
        # read-only (56.16); it never feeds back into resolution.
        knobs: dict[str, object] = {}
        provenance: dict[str, str] = {}

        # ── Layer 1: hardcoded class defaults ──────────────────────
        for param in _KNOBS:
            if hasattr(entry_cls, param):
                knobs[param] = getattr(entry_cls, param)
                provenance[param] = "class_default"

        # ── Layer 2: suite.yaml defaults ───────────────────────────
        if suite_config is not None:
            self._apply_defaults(knobs, suite_config.defaults, provenance, "suite")

        # ── Layer 3: config.yaml defaults ──────────────────────────
        self._apply_defaults(knobs, component_config.defaults, provenance, "config")

        # ── Layer 4: env (construct-by-key, ambient) ───────────────
        for param, caster in _KNOBS.items():
            key = env_key(component_name, param)
            if key in self._env:
                raw = self._env[key]
                try:
                    knobs[param] = caster(raw)
                    provenance[param] = "env"
                except (TypeError, ValueError):
                    logger.warning(
                        "Ignoring env %s=%r: not coercible to %s", key, raw, caster.__name__
                    )

        # on_critical: resolve `inherit` against the suite, then global default (§5.2).
        on_critical = self._resolve_on_critical(component_config.on_critical, suite_config)
        provenance["on_critical"] = self._on_critical_source(
            component_config.on_critical, suite_config
        )

        return ResolvedConfig(
            enabled=component_config.enabled,
            on_critical=on_critical,
            timeout_seconds=float(knobs["timeout_seconds"]),
            requests_per_second=float(knobs["requests_per_second"]),
            retry_count=int(knobs["retry_count"]),
            delay_between_targets=float(knobs["delay_between_targets"]),
            provenance=provenance,
        )

    @staticmethod
    def _apply_defaults(
        knobs: dict[str, object], defaults: Defaults, provenance: dict[str, str], label: str
    ) -> None:
        """Override knobs with any non-None field on a Defaults model (last wins),
        recording `label` as the winning layer for each value it sets."""
        for param in _KNOBS:
            value = getattr(defaults, param, None)
            if value is not None:
                knobs[param] = value
                provenance[param] = label

    @staticmethod
    def _resolve_on_critical(component_on_critical: str, suite_config: SuiteConfig | None) -> str:
        """`inherit` → suite on_critical → global default (§5.2)."""
        if component_on_critical != "inherit":
            return component_on_critical
        if suite_config is not None and suite_config.on_critical != "inherit":
            return suite_config.on_critical
        return DEFAULT_ON_CRITICAL

    @staticmethod
    def _on_critical_source(component_on_critical: str, suite_config: SuiteConfig | None) -> str:
        """Best-effort provenance for the resolved on_critical (mirrors
        `_resolve_on_critical`): a non-`inherit` component value comes from
        config.yaml (or its `annotate` default); `inherit` resolves to the suite,
        else the global default."""
        if component_on_critical != "inherit":
            return "config"
        if suite_config is not None and suite_config.on_critical != "inherit":
            return "suite"
        return "default"
