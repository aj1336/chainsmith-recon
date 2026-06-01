"""Re-export the entry class so `from app.checks.cag.cag_side_channel import SideChannelCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.cag.cag_side_channel.check import SideChannelCheck

__all__ = ["SideChannelCheck"]
