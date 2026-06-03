"""
app/routes/checks.py - Check Info Routes

Endpoints for:
- Listing available checks
- Check metadata and details
"""

import logging

from fastapi import APIRouter, HTTPException

from app.check_resolver import get_all_check_metadata
from app.engine.scanner import AVAILABLE_CHECKS, get_check_info
from app.scenarios import get_scenario_manager

logger = logging.getLogger(__name__)

router = APIRouter()


def _disabled_check_entry(meta) -> dict:
    """Shape a disabled check's metadata like a check-info dict (enabled=False).

    Disabled checks are never instantiated, so only contract/config metadata is
    available; execution-wiring fields default to empty for shape parity.
    """
    return {
        "name": meta.name,
        "description": meta.description,
        "reason": meta.reason,
        "references": [],
        "frameworks": {},
        "techniques": [],
        "conditions": [],
        "produces": [],
        "suite": meta.suite,
        "intrusive": False,
        "on_critical": meta.on_critical,
        # Shape parity with enabled entries (56.16). Disabled checks are never
        # imported, so the numeric knobs aren't resolved — only on_critical (from
        # the import-free metadata) is known; provenance is unavailable.
        "config": {
            "timeout_seconds": None,
            "requests_per_second": None,
            "retry_count": None,
            "delay_between_targets": None,
            "on_critical": meta.on_critical,
            "provenance": {},
        },
        "enabled": False,
    }


@router.get("/api/v1/checks")
async def get_available_checks(include_disabled: bool = False):
    """Get info about all available checks (reflects scenario mode).

    When a scenario is active, simulated checks overlay the real check
    registry (matched by name).  Real checks without a simulation are
    still included so the full suite is always visible.

    With `?include_disabled=true`, checks/suites turned off via `config.yaml`
    /`suite.yaml` `enabled: false` are appended (marked `enabled: false` with
    their `reason`), so the WebUI can offer a re-enable toggle (Phase 56.15).
    """
    mgr = get_scenario_manager()
    if mgr.is_active:
        simulations = mgr.get_simulations()
        # Build merged list: real checks + simulated overlays
        merged = dict(AVAILABLE_CHECKS)  # copy real checks
        for sim in simulations:
            info = get_check_info(sim)
            info["simulated"] = True
            merged[sim.name] = info  # replace real with sim
        checks = list(merged.values())
        scenario = mgr.active.name
        simulated = bool(simulations)
    else:
        checks = list(AVAILABLE_CHECKS.values())
        scenario = None
        simulated = False

    if include_disabled:
        # `enabled: true` on the live entries for shape parity (copy — don't
        # mutate the shared AVAILABLE_CHECKS dicts), then append the disabled
        # ones (those not present in the live, enabled-only registry).
        live_names = {c["name"] for c in checks}
        checks = [{**c, "enabled": True} for c in checks]
        checks += [
            _disabled_check_entry(m)
            for m in get_all_check_metadata()
            if not m.enabled and m.name not in live_names
        ]

    result = {"checks": checks, "simulated": simulated}
    if scenario is not None:
        result["scenario"] = scenario
    return result


@router.get("/api/v1/checks/{check_name}")
async def get_check_details(check_name: str):
    """Get detailed info about a specific check."""
    mgr = get_scenario_manager()
    if mgr.is_active:
        # Look in simulated checks first
        for check in mgr.get_simulations():
            if check.name == check_name:
                return get_check_info(check)
    if check_name not in AVAILABLE_CHECKS:
        raise HTTPException(404, f"Check '{check_name}' not found")
    return AVAILABLE_CHECKS[check_name]
