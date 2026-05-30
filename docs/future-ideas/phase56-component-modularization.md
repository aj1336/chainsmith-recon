# Phase 56 — Component Modularization

**Status:** Draft / pending implementation
**Supersedes:** `phase17-check-configurability.txt`, `phase43-check-subdirectory-restructure.md`
**Partially supersedes:** `module-system-design.md` (component folder shape + contracts absorbed here; external `modules/` root, routes, DB models, UI slots, and licensing remain future work)
**Prerequisite:** None. Independent of concurrent-scans.

---

## 1. Motivation

Three overlapping plans were heading toward the same physical disruption — restructuring every check, agent, advisor, and gate in the codebase. Doing them separately meant three passes over the same files. Doing them together means **one migration per component**.

What we get in one swing:

- **From phase 43:** subdirectory-per-component, co-located tests, auto-discovery loader replacing the 300-line manual import list in `check_resolver.py`.
- **From phase 17:** externalized per-component configuration (enabled, timeouts, tunables), presets, payload data files, env-var overrides, validation, WebUI config modals.
- **From module-system-design:** `contract.yaml` declaring identity + I/O, consistent folder shape across all component types (check/agent/advisor/gate), door left open for the future external `modules/` root.

The per-component work (new folder, new YAML files, moved tests) would have been the same under any of the three plans. Merging triples the return on a single disruptive pass.

---

## 2. Non-goals

- **External `modules/` root.** The second discovery root under `modules/`, UUID override resolution between roots, and community/paid tier distribution remain future work.
- **Routes / DB migrations / UI slots / licensing.** All multi-component module-system extension points stay out. Revisit after this phase lands.
- **Concurrent-scans dependency.** None. This work is independent.
- **Hot reload.** Component changes still require a restart.
- **Rewriting check logic.** Code files move and get de-duplicated with YAML; `run()` bodies do not change.

---

## 3. Folder shape

Every in-tree component (check, agent, advisor, gate) uses the same shape.

### 3.1 Check example

```
app/checks/network/ports/
├── check.py                  # check implementation
├── contract.yaml             # identity + I/O contract (loader reads this)
├── config.yaml               # tunables (timeout, rate, enabled, per-check params)
├── tests/
│   └── test_ports.py         # co-located tests
└── README.md                 # optional: deep prose docs, technique notes
```

### 3.2 Agent example

```
app/agents/adjudicator/
├── agent.py
├── contract.yaml
├── config.yaml
├── prompts/
│   ├── system.md
│   └── user.md
├── tests/
│   └── test_adjudicator.py
└── README.md
```

### 3.3 Naming convention

**Generic role-based filenames inside named folders** — the Next.js App Router pattern. The folder path carries identity; files inside fill well-known roles.

Per-component-type filenames:
- `check.py` / `agent.py` / `advisor.py` / `gate.py` — implementation
- `contract.yaml` — identity + I/O (loader reads this)
- `config.yaml` — tunables
- `tests/test_<folder>.py` — co-located tests (descriptive filename helps pytest output and `-k` selection)
- `README.md` — prose docs (optional)

**Well-known subdirs use generic names inside** (`prompts/system.md`, `migrations/001_init.sql`, `templates/detail.html`). The subdir path + parent folder already disambiguate.

**Ecosystem-reserved names** stay unchanged: `README.md`, `LICENSE`, `CHANGELOG.md`, `__init__.py`.

**Rationale.** Renaming a component is a single folder rename — no synchronized file renames, no `entry:` drift. Auto-discovery loaders (Next.js App Router, Django apps) use this shape because folder-is-the-unit / files-are-roles maps cleanly to mechanical discovery. Modern IDE tabs, Python tracebacks, grep output, and module-path log lines all carry folder context, so generic filenames don't lose legibility.

### 3.4 Loader rule

Discovery is mechanical: walk `{root}` recursively for folders containing `contract.yaml`. The folder name is the canonical slug; the loader asserts `folder_name == contract.name` and fails loud on drift.

---

## 4. `contract.yaml` schema

Machine-parseable. The loader reads this to build the registry.

```yaml
# app/checks/network/ports/contract.yaml

id: 7b3e2a94-1c6f-4d82-9a37-5e8b1f3c0d22   # UUIDv4, assigned once at authorship
name: ports                                 # human-readable slug; must match folder name
type: check                                 # check | agent | advisor | gate
description: "Scan TCP ports on discovered hosts."

entry: check.py:PortScanCheck               # role-based filename + class

# Check-specific fields
suite: network
phase: 2                                    # execution order within suite
depends_on:
  - output: services
    operator: truthy
produces:
  - open_ports

inputs:
  target: Target
  config: ref(config.yaml)

outputs:
  observations: [Observation]

side_effects: [network]                     # network | filesystem | db | none

tests:
  path: tests/
```

### 4.1 Field differences by component type

| Field | check | agent | advisor | gate |
|---|---|---|---|---|
| `suite` / `phase` / `depends_on` / `produces` | ✓ | — | — | — |
| `role` (adjudicator/coach/planner) | — | ✓ | — | — |
| `triggers` (observation.created, chat.message, …) | — | ✓ | — | — |
| `tools` (db.read, llm.call, …) | — | ✓ | — | — |
| `prompts` (system, user paths) | — | ✓ | — | — |
| `side_effects` | ✓ | ✓ | ✓ | ✓ |
| `outputs` | observations | adjudications/plans/coaching | recommendations | GateDecision |

Mirrors the contracts sketched in `module-system-design.md` §6.

---

## 5. `config.yaml` schema

Tunables only — runtime knobs the operator may override. Identity lives in `contract.yaml`.

```yaml
# app/checks/network/ports/config.yaml

enabled: true                               # false → loader skips the check
on_critical: annotate                       # annotate | skip_downstream | stop | inherit

defaults:
  timeout_seconds: 30
  requests_per_second: 10
  retry_count: 1

parameters:
  port_profile: ai
  scan_intensity: standard
```

### 5.1 Resolution order (last wins)

1. Hardcoded class default
2. `config.yaml` defaults
3. Suite-level defaults (future — deferred; no concrete need yet)
4. User override file (future)
5. Runtime (CLI flag, API param, preset selection)
6. Env var: `CHAINSMITH_<COMPONENT_NAME>_<PARAM>` (all uppercase, hyphens → underscores)

---

## 6. Auto-discovery loader

Replaces `get_real_checks()` in `check_resolver.py`. New file: `app/component_loader.py`.

```python
def discover_components(
    root: Path,
    component_type: Literal["check", "agent", "advisor", "gate"],
) -> list[BaseComponent]:
    """
    Walk {root} recursively for folders containing contract.yaml.
    For each match:
      1. Parse contract.yaml
      2. Parse config.yaml if present
      3. Skip if config.enabled is false
      4. Import contract.entry file, find the declared class
      5. Instantiate via from_config() with merged config
      6. Validate folder_name == contract.name; fail loud on mismatch
      7. Return phase-ordered list (for checks; stable sort otherwise)
    """
```

- **Phase ordering** for checks: `(suite_order, phase)`. Agents/advisors/gates don't have execution phases.
- **Validation:** fail loud at startup on missing required fields, mismatched filename/folder, broken entry references, UUID collisions.
- **Caching (deferred):** `.chainsmith/component-index.json` keyed by contract path + mtime, per module-system-design §8.1. Not needed day one; add if startup gets slow.

---

## 7. Rollout phases

| # | Sub-phase | Scope | Risk |
|---|-----------|-------|------|
| 56.1 | **Foundation.** Loader, `contract.yaml` + `config.yaml` schemas, `BaseCheck.from_config()`, folder-name / contract-name lint, migration tooling (`chainsmith dev new-check` + `migrate-check` + `migrate-suite` — detail in §8). Validate with a single pilot check. | Low |
| 56.2 | **Web suite** (23 checks). First full-suite migration. Exercises loader edge cases at real scale. | Medium |
| 56.3 | **Network suite** (13 checks). | Medium |
| 56.4 | **AI suite** (18 checks). | Medium |
| 56.5 | **MCP suite** (18 checks). | Medium |
| 56.6 | **Agent-check suite** (16 checks). Named to avoid confusion with the agent *component type* in 56.10. | Medium |
| 56.7 | **RAG suite** (17 checks). | Medium |
| 56.8 | **CAG suite** (17 checks). | Medium |
| 56.9 | **Check-resolver cleanup.** Delete `infer_suite()`, shrink `check_resolver.py`, drop dead imports, remove migration-shim re-exports from `__init__.py` files (or keep them — see §12 Q1). | Low |
| 56.10 | **Agents component type.** Port `app/agents/*` (coach, adjudicator, triage, etc.) to the folder shape. | Medium |
| 56.11 | **Advisors component type.** Port `app/advisors/*` to folder shape. | Low |
| 56.12 | **Gates component type.** Port Guardian's gate logic (engagement window, scope, rate limit, etc.) to folder shape. Touches the scan chokepoint — extra care. | Medium |
| 56.13 | **Phase-17 Wave 2:** externalize payload data (`data/payloads/`, `data/wordlists/`, `data/endpoints/`). | Low |
| 56.14 | **Phase-17 Wave 3:** presets (quick, thorough, passive, ai-focused). | Low |
| 56.15 | **Phase-17 Wave 4:** per-component `enabled` flag wired end-to-end + per-check `on_critical` override. | Low |
| 56.16 | **Phase-17 Wave 5:** env-var overrides + startup config validation. | Low |
| 56.17 | **Phase-17 Wave 6:** WebUI check detail modals + per-check parameter editing. | Medium |

**Each sub-phase is a separate PR.** Suites in 56.2–56.8 are independent; one stuck PR doesn't block the others. Component-type phases (56.10–56.12) can run in parallel with the phase-17 waves (56.13–56.17) — different files.

---

## 8. Migration tooling (sub-phase 56.1 detail)

Sub-phase 56.1 ships the CLI surface that makes 56.2–56.8 mostly mechanical. The goal is to minimize the per-check reasoning cost — both human and AI — by deriving every derivable field and leaving clearly-marked TODOs for the rest.

### 8.1 Commands

- **`chainsmith dev new-check --name <name> --suite <suite>`** — scaffolds a fresh component folder with `check.py`, `contract.yaml` (UUID stubbed), `config.yaml`, `tests/test_<name>.py`. Used for all post-56.1 new work.
- **`chainsmith dev migrate-check <path>`** — takes a flat check file (e.g. `app/checks/web/robots_txt.py`), creates the folder, moves files, derives the YAMLs, updates the suite's `__init__.py` re-export, and removes the entry from `check_resolver.get_real_checks()`. Supports `--dry-run`.
- **`chainsmith dev migrate-suite <suite>`** — driver that runs `migrate-check` for every flat check in a suite, then `pytest tests/<suite>/`. Fails fast with a per-check status report.
- **`chainsmith dev diff-registry --before <sha> --after HEAD`** — loads the check registry at two commits and diffs them. Confirms every pre-existing check still loads with the same `(name, suite, phase)` triple. Catches silent drops or reorderings across a suite migration.

### 8.2 Deterministic field derivation

The tool generates these fields without any LLM call — all parseable from the source file:

| Field | How |
|---|---|
| `contract.id` | `uuid4()` |
| `contract.name` | folder name |
| `contract.type` | CLI arg (`check` / `agent` / `advisor` / `gate`) |
| `contract.entry` | `check.py:<ClassName>` — class name via AST walk for the first `BaseCheck` subclass |
| `contract.suite` | folder path (`app/checks/web/...` → `web`) |
| `contract.phase` | existing class attribute if present |
| `contract.depends_on` | AST/grep for `state.get(<key>)` calls → list of keys |
| `contract.produces` | AST/grep for `self.produce(<key>)` or `Observation(kind=<key>)` patterns |
| `contract.side_effects` | imports (`requests`/`httpx` → `network`, `sqlite3`/`sqlalchemy` → `db`, `open`/`pathlib` → `filesystem`) |
| `contract.description` | first line of the class docstring |
| `config.enabled` | `true` |
| `config.defaults.*` | class attributes matching known knobs (`timeout_seconds`, `requests_per_second`, `retry_count`) |

Fields the tool can't confidently derive get written as `TODO:` so a grep (`rg 'TODO:' app/checks/`) surfaces everything needing review:

```yaml
description: "TODO: short description"
produces:
  - TODO
```

### 8.3 Optional: local LLM assist (Qwen via Ollama)

For fields where regex/AST is brittle — non-standard `depends_on` patterns, terse docstrings needing cleanup, unusual import-to-side-effect mappings — a local Qwen model can fill TODOs without burning API tokens or leaving the machine.

**Setup:**
- [Ollama](https://ollama.com) installed (single install, no API keys, runs as a background service).
- `ollama pull qwen2.5-coder:14b` — code-trained, Apache 2.0, strong at structured output. Use `:7b` on modest hardware or `:32b` on capable GPUs.
- The migration tool talks to Ollama's OpenAI-compatible endpoint at `http://localhost:11434/v1` — swap providers trivially.

**Invocation:**
```
chainsmith dev migrate-check <path>                              # deterministic only; TODOs stay as TODOs
chainsmith dev migrate-check <path> --infer=ollama:qwen2.5-coder:14b   # fill TODOs via local model
```

**Per-field prompting strategy** (one field per call — easier to validate, cheaper to retry):
- `description`: source docstring + `"Return one sentence, present tense, under 80 chars."`
- `depends_on` / `produces`: check source + schema excerpt + `"Return a JSON list of strings; empty list if unclear."`
- `side_effects`: import list + `"Return a JSON subset of [network, filesystem, db, none]."`

**Never ask the model for:** `id`, `name`, `type`, `entry`, `suite`, `phase`. These are deterministic and load-bearing — wrong values silently break the loader.

**Validation gate:** every model-generated field passes JSON-schema validation before it's written. On validation failure or Ollama unavailability, leave the `TODO:` in place and log — never merge malformed output.

**Why local matters here:** the migration touches 120+ checks. Batch-calling a hosted API for that many contract-inference calls is both costly and leaks source to a third party. Local inference is free after setup, private, and batch-friendly (run overnight, review the TODOs that remain in the morning).

### 8.4 Token-saving workflow

The intended cadence for 56.2–56.8:

1. Run `migrate-suite <suite>` locally (deterministic pass).
2. Run again with `--infer` to fill TODOs via Qwen.
3. Review remaining `TODO:` markers by hand — typically 2–5 per suite.
4. Run the suite tests. If green, commit.
5. Only involve Claude for failing tests or ambiguous TODOs the local model couldn't resolve.

This compresses the per-suite Claude conversation from "walk me through 20 migrations" to "here are 3 TODOs and 1 failing test — help?"

---

## 9. Per-check migration checklist

For each check in a suite:

- [ ] Create `app/checks/<suite>/<check_name>/` folder
- [ ] Move the check file → `check.py`
- [ ] Write `contract.yaml` (generate UUID if none exists; `name:` must match folder name)
- [ ] Write `config.yaml` from existing class attributes
- [ ] Move/split tests → `tests/test_<check_name>.py` (delete the original — do not leave a duplicate)
- [ ] Update suite's `__init__.py` to re-export from the new path (migration shim)
- [ ] Run full suite tests — zero regression

After all checks in a suite are migrated:

- [ ] Remove the suite's entries from `check_resolver.get_real_checks()`
- [ ] Verify the loader picks up the suite in the same phase order as before
- [ ] Verify scan produces identical observations on a reference scenario (fakobanko)

---

## 10. Risks

1. **Wide refactor.** Touching every check is inherently risky. Mitigated by per-suite PRs + full test run after each. Reference-scenario comparison (fakobanko) catches silent behavior drift.
2. **Test discovery.** Co-located `tests/` subdirs must be on `pytest.ini` `testpaths`. Watch for double-collection — delete the original test file as you migrate, don't leave it behind.
3. **Import-path changes.** Existing `from app.checks.web.robots import RobotsTxtCheck` callers work via the folder's `__init__.py` re-export. Keep as a migration shim; removal in 56.9 is optional (see §12 Q1).
4. **UUID authorship burden.** One-time cost per component. The `chainsmith dev new-check` scaffold from 56.1 generates UUID + folder + skeleton files so contributors never hand-write one.
5. **Contract drift from code.** If `contract.yaml` declares `produces: open_ports` but the code never sets it, the loader can't catch that at parse time. Add a test-suite rule that runs each check against a mock target and validates declared outputs match actual. Defer to 56.9 if it slows the migration.
6. **Gate migration touching Guardian.** 56.12 reshapes the scan chokepoint. Carry extra test coverage; validate engagement-window enforcement and scope gating behave identically before/after.

---

## 11. Success criteria

- `pytest tests/` passes with zero regressions across 56.1–56.12.
- `check_resolver.py` drops below 100 lines (from ~300).
- `infer_suite()` deleted.
- Every in-tree component lives in a folder matching §3.
- Every component folder contains the role-based filenames from §3.3 (`check.py`/`agent.py`/`advisor.py`/`gate.py` + `contract.yaml` + `config.yaml`) and its `contract.name` matches the folder name.
- Adding a new check: run `chainsmith dev new-check --name foo --suite web` → edit the generated `foo.py` → done. No `check_resolver.py` edit.
- Operators can disable a check via `{check}.config.yaml: enabled: false` (effective next restart).
- Fakobanko scenario produces bit-identical observation counts pre- and post-migration (or documented diffs for explained behavior changes).

---

## 12. Open questions

1. **`__init__.py` re-export shims: keep permanent or remove in 56.9?** Keeping means `from app.checks.web.robots import RobotsTxtCheck` works forever (good for any external callers). Removing enforces the new path (cleaner). Lean: keep permanent — cost is near zero.
2. **Contract validation depth.** Should the loader validate that `produces:` outputs are actually set by the check at runtime, or is that purely a test-suite concern? Lean: test-suite, with a `chainsmith verify contracts` dev command.
3. **When to add the UUID override mechanism?** Not needed for in-tree work. Defer until the external `modules/` root phase. UUIDs in contracts now are forward-compat — the override wire is the future bit.
4. **Suite-level `suite.yaml`?** Phase 43 proposed it for shared defaults. No concrete need yet — per-check config covers it. Revisit if duplication emerges across a suite.
5. **Template / scaffold location.** `chainsmith dev new-check` needs a template folder. `app/dev/templates/component/` or `tools/templates/`?

---

## Summary

One folder shape across all in-tree components. Generic role-based filenames inside named folders, Next.js App Router style: `check.py`/`agent.py`/`advisor.py`/`gate.py` + `contract.yaml` + `config.yaml`. The folder path carries identity; files fill well-known roles. `contract.yaml` is identity + I/O (machine-parseable); `config.yaml` is tunables; code and tests live next to them. Auto-discovery loader replaces hand-maintained registries. Phase-17's configurability, phase-43's restructure, and the module-system component shape all land in one coherent pass, scoped per suite so the blast radius stays bounded.

The external `modules/` root, routes/DB/UI extension points, and licensing remain future work, tracked in `module-system-design.md`. When that phase lands, in-tree components are already in the right shape — a folder move is all it takes to promote one to a module.
