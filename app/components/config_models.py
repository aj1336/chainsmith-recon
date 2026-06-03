"""
app/components/config_models.py - `config.yaml` / `suite.yaml` source models (Phase 56 §5).

These are the per-source Pydantic models the `ConfigResolver` (§5.1) layers
together. Tunable knobs are `Optional` (None = "unset at this layer") so the
resolver can merge general→specific with last-non-None winning, without a
broad layer clobbering a narrow one with a default.

Identity lives in `contract.yaml`; these hold only runtime knobs an operator
may safely retune (§5.3 ownership rule). The two config systems
(`ChainsmithConfig` and this) stay separate — see §5.3.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# What to do when this component yields a CRITICAL observation.
# `inherit` resolves to the suite's on_critical, then the global default (§5.2).
OnCritical = Literal["annotate", "skip_downstream", "stop", "inherit"]

# Global fallback when nothing sets on_critical anywhere.
DEFAULT_ON_CRITICAL: str = "annotate"


class Defaults(BaseModel):
    """The standard tunable knob set (§8.2). All optional for layering."""

    model_config = ConfigDict(extra="forbid")

    timeout_seconds: float | None = None
    requests_per_second: float | None = None
    retry_count: int | None = None
    delay_between_targets: float | None = None


class ComponentConfig(BaseModel):
    """Parsed `config.yaml` for a single component (§5).

    `parameters` holds per-component custom knobs that fall outside the standard
    `defaults` set. For *checks* it stays empty — their custom tunables remain
    class attributes until the phase-17 WebUI wave (§5 note). For *agents* it
    carries construction/engine knobs migrated out of `ChainsmithConfig` in
    56.10c (e.g. coach `memory_cap`, researcher `offline_mode`, the adjudicator/
    triage `context_file`, triage `kb_path`). `from_spec()` forwards the subset
    the agent constructor accepts; the rest are read via the registry accessor.
    """

    model_config = ConfigDict(extra="forbid")

    enabled: bool = True  # false → loader skips the component
    reason: str = ""  # optional human note (e.g. why disabled); surfaced in introspection (56.15)
    on_critical: OnCritical = "annotate"
    defaults: Defaults = Field(default_factory=Defaults)
    parameters: dict[str, object] = Field(default_factory=dict)


class SuiteConfig(BaseModel):
    """Parsed `suite.yaml` — defaults shared by every check in a suite (§5.2)."""

    model_config = ConfigDict(extra="forbid")

    name: str
    enabled: bool = True  # false → loader skips the whole suite
    on_critical: OnCritical = "annotate"  # parent for a check's on_critical: inherit
    defaults: Defaults = Field(default_factory=Defaults)


@dataclass
class ResolvedConfig:
    """The fully-resolved load-time baseline (§5.1 layers 1-4) for one component.

    Produced by `ConfigResolver.resolve()` and applied onto the instance by
    `BaseCheck.from_config()`. Per-scan overrides (layer 6) are applied later in
    the scan path, never baked in here.
    """

    enabled: bool
    on_critical: str
    timeout_seconds: float
    requests_per_second: float
    retry_count: int
    delay_between_targets: float
