"""Re-export the entry class so `from app.checks.ai.conversation_history_leak import ConversationHistoryLeakCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.ai.conversation_history_leak.check import ConversationHistoryLeakCheck

__all__ = ["ConversationHistoryLeakCheck"]
