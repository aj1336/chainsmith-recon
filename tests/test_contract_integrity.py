"""Contract-integrity CI gate (Phase 56 §8.6).

The primary enforcement of the naming/identity/placement rules: it runs inside
the existing `pytest tests/` step (which already blocks PRs), calling the same
`verify_contracts()` the loader and `chainsmith dev verify-contracts` call — so
"what CI enforces" can never drift from "what the loader enforces."
"""

from pathlib import Path

from app.component_loader import verify_contracts

_APP = Path(__file__).resolve().parent.parent / "app"
CHECKS_ROOT = _APP / "checks"
AGENTS_ROOT = _APP / "agents"


def test_check_contracts_have_no_violations():
    violations = verify_contracts(CHECKS_ROOT, "check")
    assert not violations, "Component contract violations:\n" + "\n".join(
        f"  - {v}" for v in violations
    )


def test_agent_contracts_have_no_violations():
    violations = verify_contracts(AGENTS_ROOT, "agent")
    assert not violations, "Agent contract violations:\n" + "\n".join(
        f"  - {v}" for v in violations
    )
