"""Contract-integrity CI gate (Phase 56 §8.6).

The primary enforcement of the naming/identity/placement rules: it runs inside
the existing `pytest tests/` step (which already blocks PRs), calling the same
`verify_contracts()` the loader and `chainsmith dev verify-contracts` call — so
"what CI enforces" can never drift from "what the loader enforces."
"""

from pathlib import Path

from app.component_loader import verify_contracts

CHECKS_ROOT = Path(__file__).resolve().parent.parent / "app" / "checks"


def test_check_contracts_have_no_violations():
    violations = verify_contracts(CHECKS_ROOT, "check")
    assert not violations, "Component contract violations:\n" + "\n".join(
        f"  - {v}" for v in violations
    )
