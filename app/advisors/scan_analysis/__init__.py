"""Scan-analysis advisor component (Phase 56 folder shape, 56.11).

Re-exports the public surface so existing imports
(`from app.advisors.scan_analysis import ScanAnalysisAdvisor`) and the lazy
`app.advisors` accessor resolve to the same objects.
"""

from app.advisors.scan_analysis.advisor import (
    ScanAnalysisAdvisor,
    ScanAnalysisAdvisorConfig,
    ScanAnalysisRecommendation,
    build_analysis_advisor_from_launcher,
)

__all__ = [
    "ScanAnalysisAdvisor",
    "ScanAnalysisAdvisorConfig",
    "ScanAnalysisRecommendation",
    "build_analysis_advisor_from_launcher",
]
