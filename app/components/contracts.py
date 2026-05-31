"""
app/components/contracts.py - The authoritative `contract.yaml` schema (Phase 56 §4).

The loader parses `contract.yaml` into these Pydantic v2 models
(`CheckContract(**yaml_data)`), so required/optional fields, types, enums, and
UUID format are declared once, here, in code. The illustrative YAML in the
design doc is generated to match this model and cannot silently drift.

Pydantic at the I/O boundary; the runtime domain objects (e.g. the
`CheckCondition` dataclass in `app/checks/base.py`) are converted from these at
load time. Each `Condition` below mirrors that dataclass.

Only the `check` variant is concrete this phase. Agent/advisor/gate contracts
are sibling models discriminated on `type` and land with 56.10-56.12 (§4.1).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import UUID4, BaseModel, ConfigDict, Field

# Operators accepted on a dependency condition — mirrors CheckCondition.evaluate.
ConditionOperator = Literal["exists", "equals", "contains", "truthy", "gte", "lte"]

# Allowed side-effect tags (§4 / §8.2 import-derived).
SideEffect = Literal["network", "filesystem", "db", "none"]


class Condition(BaseModel):
    """A single dependency condition. Mirrors the runtime `CheckCondition` dataclass.

    Converted to `app.checks.base.CheckCondition` at load (DTO-at-boundary →
    domain-object).
    """

    model_config = ConfigDict(extra="forbid")

    output_name: str
    operator: ConditionOperator = "exists"
    value: Any = None


class CheckContract(BaseModel):
    """Identity + I/O contract for a `check` component (§4).

    The folder name is the canonical slug and must equal `name`
    (enforced by the loader / `verify_contracts`, not here, so a mismatch is
    reported as a structural violation rather than a parse error).
    """

    model_config = ConfigDict(extra="forbid")

    # ─── identity ───────────────────────────────────────────────
    id: UUID4  # assigned once at authorship
    name: str  # slug; must match folder name
    type: Literal["check"] = "check"
    description: str
    entry: str  # "check.py:ClassName"

    # ─── execution wiring ───────────────────────────────────────
    suite: str
    depends_on: list[Condition] = Field(default_factory=list)
    produces: list[str] = Field(default_factory=list)
    # NOTE: no authored `phase`. Execution order is a runtime topological sort
    # over depends_on/produces (check_launcher.py); the UI progress phase is
    # derived from `suite`. A static phase int would be a third, unbacked
    # source of truth (§6, C1).

    # ─── safety / applicability / scheduling ────────────────────
    intrusive: bool = False
    service_types: list[str] = Field(default_factory=list)
    parallel_safe: bool = False

    # ─── I/O + metadata ─────────────────────────────────────────
    outputs: dict[str, Any] = Field(default_factory=lambda: {"observations": ["Observation"]})
    side_effects: list[SideEffect] = Field(default_factory=lambda: ["none"])
    techniques: list[str] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)
    reason: str = ""


# Registry of contract models by component type. Only `check` is concrete this
# phase; agent/advisor/gate models are added here as 56.10-56.12 land, at which
# point this becomes the discriminated union described in §4.1.
CONTRACT_MODELS: dict[str, type[BaseModel]] = {
    "check": CheckContract,
}


def contract_model_for(component_type: str) -> type[BaseModel]:
    """Return the Pydantic contract model for a component type.

    Raises KeyError for types not yet specified (agent/advisor/gate until their
    sub-phases land) so a premature use fails loudly rather than silently.
    """
    return CONTRACT_MODELS[component_type]
