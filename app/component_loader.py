"""
app/component_loader.py - Auto-discovery loader (Phase 56 §6).

Replaces the hand-maintained import list in `check_resolver.get_real_checks()`.
Discovery is mechanical: walk a type root recursively for folders containing
`contract.yaml`; the folder name is the canonical slug.

Two public entry points:

- `verify_contracts(root, type)` — passes 1-3 only. Parses + validates contracts
  and folder hygiene WITHOUT importing any entry module, returning an accumulated
  list of `Violation`. This is the shared validator called from the loader, the
  `tests/test_contract_integrity.py` CI gate, and `chainsmith dev verify-contracts`
  (§8.6) — so "what CI enforces" can never drift from "what the loader enforces."

- `discover_components(root, type)` — runs `verify_contracts`, raises once with the
  full violation list if any, then imports the survivors and builds them via
  `from_config()` with the resolved config baseline (§5.1).

Validation is global-first and does NOT fail-fast per folder: a per-folder failure
(e.g. a name mismatch) can mask the real root cause (e.g. a duplicate UUID from a
copy-paste). Errors accumulate and are reported together (§6).
"""

from __future__ import annotations

import ast
import importlib
import logging
from dataclasses import dataclass
from pathlib import Path

import yaml

from app.components.config_models import ComponentConfig, SuiteConfig
from app.components.config_resolver import ENV_DELIM, ConfigResolver
from app.components.contracts import contract_model_for

logger = logging.getLogger(__name__)

ComponentType = str  # "check" | "agent" | "advisor" | "gate"


@dataclass(frozen=True)
class Violation:
    """A single contract-integrity problem, surfaced by `verify_contracts`."""

    path: Path  # the component folder (or test file) at fault
    code: str  # machine-readable category, e.g. "duplicate-uuid"
    message: str  # human-readable detail

    def __str__(self) -> str:
        return f"[{self.code}] {self.path}: {self.message}"


class ComponentLoadError(Exception):
    """Raised by `discover_components` when `verify_contracts` finds violations."""

    def __init__(self, violations: list[Violation]):
        self.violations = violations
        body = "\n".join(f"  - {v}" for v in violations)
        super().__init__(f"{len(violations)} component contract violation(s):\n{body}")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def parse_entry(entry: str) -> tuple[str, str]:
    """Split an `entry` string ("check.py:ClassName") into (filename, class_name)."""
    filename, _, class_name = entry.partition(":")
    return filename, class_name


def _dotted_package(component_dir: Path) -> str:
    """Derive the importable dotted package for a folder by walking up through
    parents that are packages (have `__init__.py`). cwd-independent."""
    parts: list[str] = []
    d = component_dir
    while (d / "__init__.py").exists():
        parts.append(d.name)
        d = d.parent
    return ".".join(reversed(parts))


def _module_for(component_dir: Path, entry_filename: str) -> str:
    """Dotted module path for an entry file inside a component folder."""
    stem = Path(entry_filename).stem
    pkg = _dotted_package(component_dir)
    return f"{pkg}.{stem}" if pkg else stem


def _entry_class_def(tree: ast.Module, class_name: str) -> ast.ClassDef | None:
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return node
    return None


def _required_arg_names(func: ast.FunctionDef) -> list[str]:
    """Names of required (no-default) parameters of a function, excluding `self`."""
    a = func.args
    positional = a.posonlyargs + a.args
    # defaults align to the tail of positional params
    n_required_positional = len(positional) - len(a.defaults)
    required = [p.arg for p in positional[:n_required_positional] if p.arg != "self"]
    # keyword-only without a default are also required for a bare cls()
    required += [
        p.arg for p, d in zip(a.kwonlyargs, a.kw_defaults, strict=False) if d is None
    ]
    return required


# ─────────────────────────────────────────────────────────────────────────────
# verify_contracts — passes 1-3 (no imports)
# ─────────────────────────────────────────────────────────────────────────────


def verify_contracts(root: Path, component_type: ComponentType = "check") -> list[Violation]:
    """Validate every `contract.yaml` under `root` and folder hygiene (§6, §8.6).

    Never imports an entry module. Accumulates and returns all violations.
    """
    root = Path(root)
    violations: list[Violation] = []
    if not root.exists():
        return violations

    model_cls = contract_model_for(component_type)

    # ── Pass 1: parse & collect (fail only on unparseable YAML) ──
    entries: list[tuple[Path, dict, object | None]] = []
    for contract_path in sorted(root.rglob("contract.yaml")):
        comp_dir = contract_path.parent
        try:
            raw = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            violations.append(Violation(comp_dir, "yaml-parse", f"contract.yaml unparseable: {e}"))
            continue
        if not isinstance(raw, dict):
            violations.append(
                Violation(comp_dir, "yaml-parse", "contract.yaml is not a mapping")
            )
            continue
        model = None
        try:
            model = model_cls(**raw)
        except Exception as e:  # pydantic ValidationError (and any constructor error)
            for line in str(e).splitlines():
                violations.append(Violation(comp_dir, "contract-schema", line.strip()))
        entries.append((comp_dir, raw, model))

    # ── Pass 2: global identity (canonical invariants, accumulate) ──
    by_uuid: dict[str, Path] = {}
    by_name: dict[str, Path] = {}
    for comp_dir, raw, model in entries:
        uid = str(model.id) if model is not None else raw.get("id")
        name = model.name if model is not None else raw.get("name")
        if uid:
            if uid in by_uuid:
                violations.append(
                    Violation(
                        comp_dir,
                        "duplicate-uuid",
                        f"UUID {uid} also used by {by_uuid[uid]}",
                    )
                )
            else:
                by_uuid[uid] = comp_dir
        if name:
            if name in by_name:
                violations.append(
                    Violation(
                        comp_dir,
                        "duplicate-name",
                        f"name '{name}' also used by {by_name[name]}",
                    )
                )
            else:
                by_name[name] = comp_dir

    # ── Pass 3: per-component hygiene (accumulate) ──
    for comp_dir, raw, model in entries:
        name = model.name if model is not None else raw.get("name")
        if name:
            if comp_dir.name != name:
                violations.append(
                    Violation(
                        comp_dir,
                        "folder-name-mismatch",
                        f"folder '{comp_dir.name}' != contract.name '{name}'",
                    )
                )
            if ENV_DELIM in name:
                violations.append(
                    Violation(
                        comp_dir,
                        "double-underscore",
                        f"component name '{name}' must not contain '{ENV_DELIM}'",
                    )
                )
        if model is not None:
            violations.extend(_verify_entry_constructible(comp_dir, model.entry))

    # ── Pass 3 (cont.): test-placement guard (§10 risk 2) ──
    for test_file in sorted(root.rglob("test_*.py")):
        parent = test_file.parent
        if parent.name != "tests" or not (parent.parent / "contract.yaml").exists():
            violations.append(
                Violation(
                    test_file,
                    "test-misplaced",
                    "test_*.py under a component root must live in <component>/tests/",
                )
            )

    return violations


def _verify_entry_constructible(comp_dir: Path, entry: str) -> list[Violation]:
    """AST-assert the entry class exists and is no-arg constructible (§6/§8.6)."""
    violations: list[Violation] = []
    filename, class_name = parse_entry(entry)
    if not filename or not class_name:
        return [Violation(comp_dir, "entry-malformed", f"entry '{entry}' must be 'file.py:Class'")]
    entry_path = comp_dir / filename
    if not entry_path.exists():
        return [Violation(comp_dir, "entry-missing", f"entry file '{filename}' not found")]
    try:
        tree = ast.parse(entry_path.read_text(encoding="utf-8"))
    except SyntaxError as e:
        return [Violation(comp_dir, "entry-syntax", f"{filename}: {e}")]
    class_def = _entry_class_def(tree, class_name)
    if class_def is None:
        return [
            Violation(comp_dir, "entry-class-missing", f"class '{class_name}' not in {filename}")
        ]
    for node in class_def.body:
        if isinstance(node, ast.FunctionDef) and node.name == "__init__":
            required = _required_arg_names(node)
            if required:
                violations.append(
                    Violation(
                        comp_dir,
                        "entry-not-no-arg",
                        f"{class_name}.__init__ requires {required}; must be no-arg constructible",
                    )
                )
            break
    return violations


# ─────────────────────────────────────────────────────────────────────────────
# discover_components — adds pass 4 (import + construct)
# ─────────────────────────────────────────────────────────────────────────────


def _load_suite_config(root: Path, suite: str) -> SuiteConfig | None:
    """Read `<root>/<suite>/suite.yaml` for precedence layer 2 (§5.2). Missing is fine."""
    suite_yaml = root / suite / "suite.yaml"
    if not suite_yaml.exists():
        return None
    raw = yaml.safe_load(suite_yaml.read_text(encoding="utf-8")) or {}
    raw.setdefault("name", suite)
    return SuiteConfig(**raw)


def discover_components(root: Path, component_type: ComponentType = "check") -> list:
    """Discover, validate, and instantiate every enabled component under `root` (§6).

    Returns a suite-grouped, stable-sorted list (deterministic discovery output;
    runtime execution order is decided later by check_launcher.py over the
    conditions/produces DAG).
    """
    root = Path(root)
    violations = verify_contracts(root, component_type)
    if violations:
        raise ComponentLoadError(violations)

    model_cls = contract_model_for(component_type)
    resolver = ConfigResolver()
    built: list[tuple[str, str, object]] = []

    for contract_path in sorted(root.rglob("contract.yaml")):
        comp_dir = contract_path.parent
        contract = model_cls(**yaml.safe_load(contract_path.read_text(encoding="utf-8")))

        # config.yaml (per-component) — disabled components are skipped (§6).
        cfg_path = comp_dir / "config.yaml"
        if cfg_path.exists():
            comp_cfg = ComponentConfig(**(yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}))
        else:
            comp_cfg = ComponentConfig()
        if not comp_cfg.enabled:
            logger.info("Skipping disabled component: %s", contract.name)
            continue

        suite = comp_dir.relative_to(root).parts[0]
        suite_cfg = _load_suite_config(root, suite)
        if suite_cfg is not None and not suite_cfg.enabled:
            logger.info("Skipping component in disabled suite '%s': %s", suite, contract.name)
            continue

        filename, class_name = parse_entry(contract.entry)
        module_name = _module_for(comp_dir, filename)
        mod = importlib.import_module(module_name)
        entry_cls = getattr(mod, class_name)

        resolved = resolver.resolve(contract.name, entry_cls, comp_cfg, suite_cfg)
        instance = entry_cls.from_config(contract, resolved)
        built.append((suite, contract.name, instance))

    built.sort(key=lambda t: (t[0], t[1]))
    logger.info("Discovered %d %s component(s)", len(built), component_type)
    return [inst for _, _, inst in built]
