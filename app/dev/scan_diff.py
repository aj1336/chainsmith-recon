"""
app/dev/scan_diff.py - Scenario scan observation baseline + diff (Phase 56 §9 anchor #2).

The behavior anchor that complements `registry_diff` (identity) with *observable
output*: run a scenario scan and capture the multiset of observation identities,
so a suite migration can be proven to produce the same observations before/after.

Unlike the other `app/dev/` tools (serverless source authoring), this one talks
to a running Chainsmith server — a scan is inherently a server operation. The
workflow for 56.2+ is: capture a baseline BEFORE migrating a suite, migrate,
then `--compare` after.

Observation identity is `(check_name, host, severity, title)` — the runner-assigned
sequential id and volatile evidence text are excluded so the comparison is stable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def observation_identity(obs: dict) -> tuple[str, str, str, str]:
    host = obs.get("target_host") or obs.get("host") or ""
    return (
        obs.get("check_name") or "",
        host,
        obs.get("severity") or "",
        obs.get("title") or "",
    )


def run_scenario_scan(
    client,
    target: str,
    scenario: str,
    suites: list[str] | None = None,
    parallel: bool = False,
) -> list[dict]:
    """Set scope, load the scenario, run a scan to completion, return observations."""
    client.set_scope(target, [])
    client.update_settings(parallel=parallel)
    client.load_scenario(scenario)
    client.start_scan(suites=suites)
    result = client.poll_scan(interval=1.0)
    if result.get("status") == "error":
        raise RuntimeError(f"Scan errored: {result.get('error', 'unknown')}")
    return client.get_observations().get("observations", [])


def snapshot_from_observations(observations: list[dict]) -> dict[str, Any]:
    """Build a stable, comparable snapshot from a list of observation dicts."""
    identities = sorted(list(observation_identity(o)) for o in observations)
    by_check: dict[str, int] = {}
    for o in observations:
        name = o.get("check_name") or "?"
        by_check[name] = by_check.get(name, 0) + 1
    return {
        "total": len(observations),
        "by_check": dict(sorted(by_check.items())),
        "identities": identities,
    }


def save_baseline(path: Path, snapshot: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(snapshot, indent=2, sort_keys=True), encoding="utf-8")


def compare(baseline_path: Path, current: dict[str, Any]) -> dict[str, Any]:
    """Diff a current snapshot against a saved baseline.

    Returns {clean, total_baseline, total_current, added, removed, by_check_delta}.
    `added`/`removed` are observation-identity tuples (as lists).
    """
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    b_ids = {tuple(x) for x in baseline.get("identities", [])}
    c_ids = {tuple(x) for x in current.get("identities", [])}

    added = sorted(list(x) for x in (c_ids - b_ids))
    removed = sorted(list(x) for x in (b_ids - c_ids))

    b_by, c_by = baseline.get("by_check", {}), current.get("by_check", {})
    by_check_delta = {
        name: [b_by.get(name, 0), c_by.get(name, 0)]
        for name in sorted(set(b_by) | set(c_by))
        if b_by.get(name, 0) != c_by.get(name, 0)
    }

    return {
        "clean": not (added or removed),
        "total_baseline": baseline.get("total"),
        "total_current": current.get("total"),
        "added": added,
        "removed": removed,
        "by_check_delta": by_check_delta,
    }
