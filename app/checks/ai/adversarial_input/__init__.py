"""Re-export the entry class so `from app.checks.ai.adversarial_input import AdversarialInputCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.adversarial_input.check import AdversarialInputCheck

__all__ = ["AdversarialInputCheck"]
