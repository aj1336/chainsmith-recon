"""Re-export the entry class so `from app.checks.web.robots_txt import RobotsTxtCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.robots_txt.check import RobotsTxtCheck

__all__ = ["RobotsTxtCheck"]
