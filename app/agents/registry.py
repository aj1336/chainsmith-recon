"""
app/agents/registry.py - Agent discovery + factory (Phase 56 §6, sub-phase 56.10).

The check loader (`discover_components`) builds no-arg startup singletons and
returns *instances*. Agents can't use that path: they need a runtime
`LLMClient` and a per-session `event_callback`, and are built per
request/session (see `app/agents/base.py`). So discovery here returns *specs*
(contract + resolved config + entry class), and a thin factory constructs
instances on demand:

    AGENTS = discover_agent_specs()                 # registry of specs
    agent = AGENTS.create("adjudicator",            # built per request/session
                          client=get_llm_client(),
                          event_callback=session_cb)

It reuses the shared `verify_contracts()` gate and the loader's path helpers, so
agent folders are held to the same identity/placement invariants as checks.
"""

from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

from app.component_loader import (
    ComponentLoadError,
    _module_for,
    parse_entry,
    verify_contracts,
)
from app.components.config_models import ComponentConfig
from app.components.contracts import AgentContract

if TYPE_CHECKING:
    from app.agents.base import BaseAgent

logger = logging.getLogger(__name__)

# The agent type root — this package. Discovery walks it for `contract.yaml`.
AGENTS_ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True)
class AgentSpec:
    """A discovered, validated agent ready to construct on demand.

    Holds everything the factory needs except the runtime deps (client,
    event_callback), which the caller supplies to `create()`.
    """

    contract: AgentContract
    config: ComponentConfig
    entry_cls: type[BaseAgent]

    def create(self, **runtime_deps) -> BaseAgent:
        """Construct an instance, injecting runtime deps via `from_spec()`."""
        return self.entry_cls.from_spec(self.contract, self.config, **runtime_deps)


class AgentRegistry:
    """Name → `AgentSpec` lookup with a per-request construction factory."""

    def __init__(self, specs: dict[str, AgentSpec]):
        self._specs: dict[str, AgentSpec] = dict(specs)

    def __contains__(self, name: str) -> bool:
        return name in self._specs

    def names(self) -> list[str]:
        return sorted(self._specs)

    def spec(self, name: str) -> AgentSpec:
        return self._specs[name]

    def create(self, name: str, **runtime_deps) -> BaseAgent:
        """Build the named agent, injecting the supplied runtime deps."""
        if name not in self._specs:
            raise KeyError(f"no agent component named {name!r}; have {self.names()}")
        return self._specs[name].create(**runtime_deps)


def discover_agent_specs(root: Path = AGENTS_ROOT) -> AgentRegistry:
    """Walk `root` for agent `contract.yaml` folders and return a registry.

    Validates with the shared `verify_contracts()` (raises `ComponentLoadError`
    on any violation), then parses each contract/config and resolves the entry
    class — but does NOT instantiate (agents are built per request via the
    factory). Disabled components (`config.yaml: enabled: false`) are skipped.
    """
    root = Path(root)
    violations = verify_contracts(root, "agent")
    if violations:
        raise ComponentLoadError(violations)

    specs: dict[str, AgentSpec] = {}
    for contract_path in sorted(root.rglob("contract.yaml")):
        comp_dir = contract_path.parent
        contract = AgentContract(**yaml.safe_load(contract_path.read_text(encoding="utf-8")))

        cfg_path = comp_dir / "config.yaml"
        if cfg_path.exists():
            config = ComponentConfig(**(yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}))
        else:
            config = ComponentConfig()
        if not config.enabled:
            logger.info("Skipping disabled agent: %s", contract.name)
            continue

        filename, class_name = parse_entry(contract.entry)
        module = importlib.import_module(_module_for(comp_dir, filename))
        entry_cls = getattr(module, class_name)
        specs[contract.name] = AgentSpec(contract, config, entry_cls)

    logger.info("Discovered %d agent component(s)", len(specs))
    return AgentRegistry(specs)


_registry: AgentRegistry | None = None


def get_agent_registry() -> AgentRegistry:
    """Process-wide cached agent registry (discovered once, on first use)."""
    global _registry
    if _registry is None:
        _registry = discover_agent_specs()
    return _registry
