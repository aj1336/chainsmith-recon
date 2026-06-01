"""
app/check_resolver.py - Check List Builder

Builds the list of checks to run, handling:
- Real checks (default) — community + custom
- Scenario simulations (override real checks)
- Technique filtering (run only specific checks)

This is separate from execution — it just decides WHAT to run.
The CheckLauncher handles HOW to run them.

Usage:
    from app.check_resolver import resolve_checks

    checks = resolve_checks(
        techniques=["dns_enumeration", "port_scan"],  # Optional filter
        scenario_name="fakobanko"  # Optional scenario
    )
"""

import importlib
import logging

logger = logging.getLogger(__name__)


def resolve_checks(
    techniques: list[str] | None = None,
    scenario_name: str | None = None,
    check_names: list[str] | None = None,
    suites: list[str] | None = None,
) -> list:
    """
    Build the list of checks to run.

    Args:
        techniques: If provided, only run checks with these names (legacy)
        scenario_name: If provided, load this scenario and use its simulations
        check_names: If provided, only run checks matching these names
        suites: If provided, only run checks belonging to these suites

    Returns:
        List of check instances ready to run
    """
    # Get all real checks
    real_checks = get_real_checks()
    logger.info(f"Real checks available: {len(real_checks)} — {[c.name for c in real_checks]}")

    # If scenario active, merge simulations with real checks
    if scenario_name:
        checks = apply_scenario(real_checks, scenario_name)
    else:
        checks = real_checks

    # Filter by techniques if specified (legacy)
    if techniques:
        checks = filter_by_techniques(checks, techniques)

    # Filter by explicit check names
    if check_names:
        checks = [c for c in checks if c.name in check_names]
        logger.info(f"Filtered to {len(checks)} checks by names: {check_names}")

    # Filter by suites
    if suites:
        checks = filter_by_suites(checks, suites)

    logger.info(f"Final check list: {len(checks)} — {[c.name for c in checks]}")
    return checks


def get_real_checks() -> list:
    """Get all real check instances."""

    # Instantiate all checks in dependency order
    checks = [
        # Network Phase 1 (no dependencies, can run in parallel)
        # Network Phase 2 (depends on dns_enumeration)
        # Network Phase 4 (depends on services/port_scan)
        # Network Phase 5 (depends on service_probe)
        # Web Phase 1 (depends on services)
        # Web Phase 2 (depends on Phase 1)
        # Web critical observations (Phase 6a — depends on services, some use path_probe output)
        # Web Phase 4 (depends on Phase 2-3)
        # AI discovery (depends on services)
        # AI Phase 2 (depends on chat_endpoints)
        # AI Phase 3 (depends on Phase 2 results)
        # AI Phase 4 (uses filter/tool knowledge from Phase 2-3)
        # Agent Phase 1 (depends on services — discovery)
        # Agent Phase 2 (depends on agent_endpoints)
        # Agent Phase 3 (depends on Phase 2 — active probing)
        # Agent Phase 4 (depends on Phase 2-3 — framework-specific)
        # Agent Phase 5 (depends on multi-agent detection)
        # RAG Phase 1 (depends on services — discovery)
        # RAG Phase 2 (depends on rag_endpoints / vector_stores)
        # RAG Phase 3 (depends on Phase 1-2 — read-only probing)
        # RAG Phase 4 (depends on Phase 2-3 — write/intrusive)
        # RAG Phase 5 (depends on Phase 3-4 — advanced)
        # CAG Phase 1 (depends on services — discovery)
        # CAG Phase 2 (depends on cag_endpoints — infrastructure analysis)
        # CAG Phase 3 (depends on Phase 1-2 — deep probing)
        # CAG Phase 4 (active exploitation — intrusive)
        # CAG Phase 5 (advanced — infrastructure-dependent)
    ]

    logger.info(f"Loaded {len(checks)} community checks")

    # Auto-discovered components (Phase 56): checks migrated to the folder shape
    # (contract.yaml + config.yaml) are discovered here and removed from the hand
    # list above. During the suite-by-suite migration the two coexist; the hand
    # list shrinks as `discovered` grows. Replaces get_real_checks() entirely once
    # all suites are migrated (56.9).
    from pathlib import Path

    from app.component_loader import discover_components

    discovered = discover_components(Path(__file__).parent / "checks", "check")
    if discovered:
        checks.extend(discovered)
        logger.info(f"Loaded {len(discovered)} auto-discovered checks")

    # Custom checks (dynamic discovery from custom/)
    custom = _get_custom_checks()
    if custom:
        checks.extend(custom)
        logger.info(f"Loaded {len(custom)} custom checks")

    logger.info(f"Total checks available: {len(checks)}")
    return checks


def _get_custom_checks() -> list:
    """Discover and load custom checks from app/checks/custom/.

    Reads the CUSTOM_CHECK_REGISTRY from custom/__init__.py,
    imports each module, instantiates each class, and validates
    that it extends BaseCheck with well-formed metadata.

    Returns only checks that instantiate successfully.
    """
    from app.checks.base import BaseCheck
    from app.checks.custom import CUSTOM_CHECK_REGISTRY

    checks = []
    for module_name, class_name in CUSTOM_CHECK_REGISTRY:
        try:
            mod = importlib.import_module(f"app.checks.custom.{module_name}")
            cls = getattr(mod, class_name)
            if not issubclass(cls, BaseCheck):
                logger.warning(
                    f"Custom check {class_name} in {module_name} does not extend BaseCheck — skipped"
                )
                continue
            instance = cls()
            checks.append(instance)
            logger.info(f"  Custom check loaded: {instance.name}")
        except Exception as e:
            logger.warning(f"Failed to load custom check {module_name}.{class_name}: {e}")
    return checks


def apply_scenario(real_checks: list, scenario_name: str) -> list:
    """
    Apply scenario simulations to check list.

    Simulations replace real checks with the same name.
    Real checks without a simulation are kept as-is.

    Args:
        real_checks: List of real check instances
        scenario_name: Name of scenario to load

    Returns:
        Hybrid list with simulations where available
    """
    from app.scenarios import ScenarioLoadError, get_scenario_manager

    mgr = get_scenario_manager()

    # Load scenario if not already active
    if not mgr.is_active or mgr.active.name != scenario_name:
        try:
            mgr.load(scenario_name)
            logger.info(f"Loaded scenario: {scenario_name}")
        except ScenarioLoadError as e:
            logger.warning(f"Could not load scenario '{scenario_name}': {e}")
            return real_checks

    # Get simulations
    simulations = mgr.get_simulations()
    sim_by_name = {s.name: s for s in simulations}

    logger.info(
        f"Scenario '{scenario_name}' has {len(simulations)} simulations: {list(sim_by_name.keys())}"
    )

    # Build hybrid list
    result = []
    for check in real_checks:
        if check.name in sim_by_name:
            logger.info(f"  {check.name}: using SIMULATION")
            result.append(sim_by_name[check.name])
        else:
            logger.info(f"  {check.name}: using real check")
            result.append(check)

    return result


def filter_by_techniques(checks: list, techniques: list[str]) -> list:
    """
    Filter checks to only those in the techniques list.

    Args:
        checks: Full list of checks
        techniques: Names of checks to keep

    Returns:
        Filtered list
    """
    filtered = [c for c in checks if c.name in techniques]
    logger.info(f"Filtered to {len(filtered)} checks by techniques: {techniques}")
    return filtered


def filter_by_suites(checks: list, suites: list[str]) -> list:
    """
    Filter checks to only those belonging to the given suites.

    Suite is inferred from the check name since checks don't carry
    an explicit suite attribute.
    """
    filtered = [c for c in checks if infer_suite(c.name) in suites]
    logger.info(f"Filtered to {len(filtered)} checks by suites: {suites}")
    return filtered


# MCP check names after the Phase 56.5 `mcp_` prefix strip. Matched exactly (not by
# substring) because several collide with AI/agent substrings — see infer_suite().
_MCP_CHECK_NAMES = frozenset(
    {
        "auth_check",
        "discovery",
        "notification_injection",
        "prompt_injection",
        "protocol_version",
        "resource_traversal",
        "sampling_abuse",
        "schema_leakage",
        "server_fingerprint",
        "shadow_tool_detection",
        "template_injection",
        "tool_chain_analysis",
        "tool_enumeration",
        "tool_invocation",
        "tool_rate_limit",
        "transport_security",
        "undeclared_capabilities",
        "websocket_transport",
    }
)


# The seven check suites. Used by infer_suite's prefix-first check (§14.4).
_SUITE_NAMES = frozenset({"web", "network", "ai", "mcp", "agent", "rag", "cag"})


def infer_suite(check_name: str) -> str:
    """Infer the suite name from a check name."""
    name_lower = check_name.lower()
    # 56.7 (§14.4): uniform `<suite>_<name>` naming makes suite a pure prefix.
    # Check it FIRST so already-prefixed names route exactly; bare names (not yet
    # renamed this sweep) fall through to the legacy substring/_MCP_CHECK_NAMES
    # logic below. Safe because suite words only ever appear as deliberate
    # prefixes — no bare check name's first `_`-token is a suite word. When all
    # four remaining suites carry prefixes, the fallback (and _MCP_CHECK_NAMES)
    # can be deleted and this becomes the whole function.
    prefix = name_lower.split("_", 1)[0]
    if prefix in _SUITE_NAMES:
        return prefix
    # MCP checks (Phase 56.5) had their redundant `mcp_` prefix stripped, so they
    # can no longer be matched by an "mcp" substring — and several now collide with
    # AI/agent substrings (discovery→agent_discovery, prompt_injection→
    # system_prompt_injection, server_fingerprint→"fingerprint", tool_rate_limit→
    # "rate_limit"). Match the exact MCP name set first so the substring patterns
    # below never mis-grab them (and vice-versa).
    if name_lower in _MCP_CHECK_NAMES:
        return "mcp"
    suite_patterns = {
        # Legacy fallback: observations/data persisted with the pre-56.5 `mcp_`
        # prefix (e.g. simulations) still route to mcp. New stripped names are
        # handled by the exact-set check above before reaching here.
        "mcp": ["mcp"],
        "agent": ["agent"],
        "rag": ["rag"],
        "cag": ["cag"],
        "network": [
            "dns",
            "wildcard_dns",
            "geoip",
            "reverse_dns",
            "port_scan",
            "tls_analysis",
            "service_probe",
            "http_method_enum",
            "banner_grab",
            "whois_lookup",
            "traceroute",
            "ipv6_discovery",
        ],
        "web": [
            "header",
            "robots",
            "path",
            "openapi",
            "cors",
            "webdav",
            "vcs_exposure",
            "config_exposure",
            "directory_listing",
            "default_creds",
            "debug_endpoints",
            "cookie_security",
            "auth_detection",
            "waf_detection",
            "sitemap",
            "redirect_chain",
            "error_page",
            "ssrf_indicator",
            "favicon",
            "http2_detection",
            "hsts_preload",
            "sri",
            "mass_assignment",
        ],
        "ai": [
            "llm",
            "embedding",
            "model_info",
            "fingerprint",
            "error",
            "tool_discovery",
            "prompt",
            "rate_limit",
            "filter",
            "context",
            "jailbreak",
            "multi_turn",
            "input_format",
            "model_enum",
            "token_cost",
            "system_prompt_injection",
            "output_format",
            "api_parameter",
        ],
    }
    for suite, patterns in suite_patterns.items():
        if any(p in name_lower for p in patterns):
            return suite
    return "other"


def get_check_by_name(name: str):
    """Get a single check instance by name."""
    checks = get_real_checks()
    for c in checks:
        if c.name == name:
            return c
    return None
