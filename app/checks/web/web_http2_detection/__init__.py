"""Re-export the entry class so `from app.checks.web.web_http2_detection import HTTP2DetectionCheck` resolves to
the same class object the loader instantiates (identity-preserving, §3.1)."""

from app.checks.web.web_http2_detection.check import HTTP2DetectionCheck

__all__ = ["HTTP2DetectionCheck"]
