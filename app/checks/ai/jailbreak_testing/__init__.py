"""Re-export the entry class so `from app.checks.ai.jailbreak_testing import JailbreakTestingCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.jailbreak_testing.check import JailbreakTestingCheck

__all__ = ["JailbreakTestingCheck"]
