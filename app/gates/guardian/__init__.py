"""Guardian gate component (Phase 56 folder shape, 56.12).

Re-exports the public surface so existing imports
(`from app.gates.guardian import Guardian`) and the lazy `app.gates` accessor
resolve to the same object.
"""

from app.gates.guardian.gate import Guardian

__all__ = ["Guardian"]
