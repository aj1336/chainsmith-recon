"""Scan-planner advisor component (Phase 56 folder shape, 56.11).

Re-exports the public surface so existing imports
(`from app.advisors.scan_planner import ScanPlannerAdvisor`) and the lazy
`app.advisors` accessor resolve to the same objects.
"""

from app.advisors.scan_planner.advisor import (
    ScanPlannerAdvisor,
    ScanPlannerRecommendation,
)

__all__ = ["ScanPlannerAdvisor", "ScanPlannerRecommendation"]
