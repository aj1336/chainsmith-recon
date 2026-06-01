"""
Web Checks

HTTP/web-specific reconnaissance:
- Security headers analysis (with value grading)
- Cookie security analysis
- Authentication detection
- WAF/CDN detection
- robots.txt and sitemap discovery
- Path/directory enumeration
- CORS misconfiguration testing
- OpenAPI/Swagger documentation discovery
- Critical observations: WebDAV, VCS exposure, config secrets, directory listing,
  default credentials, debug endpoints (Phase 6a)
- Content & structure discovery: sitemap parsing, redirect chains,
  error page fingerprinting, SSRF indicators (Phase 6c)
- Additional protocol & analysis: favicon fingerprinting, HTTP/2-3 detection,
  HSTS preload verification, SRI check, mass assignment (Phase 6d)
"""

from app.checks.web.web_auth_detection import AuthDetectionCheck
from app.checks.web.web_config_exposure import ConfigExposureCheck
from app.checks.web.web_cookie_security import CookieSecurityCheck
from app.checks.web.web_cors import CorsCheck
from app.checks.web.web_debug_endpoints import DebugEndpointCheck
from app.checks.web.web_default_creds import DefaultCredsCheck
from app.checks.web.web_directory_listing import DirectoryListingCheck
from app.checks.web.web_error_page import ErrorPageCheck
from app.checks.web.web_favicon import FaviconCheck
from app.checks.web.web_header_analysis import HeaderAnalysisCheck
from app.checks.web.web_hsts_preload import HSTSPreloadCheck
from app.checks.web.web_http2_detection import HTTP2DetectionCheck
from app.checks.web.web_mass_assignment import MassAssignmentCheck
from app.checks.web.web_openapi_discovery import OpenAPICheck
from app.checks.web.web_path_probe import PathProbeCheck
from app.checks.web.web_redirect_chain import RedirectChainCheck
from app.checks.web.web_robots_txt import RobotsTxtCheck
from app.checks.web.web_sitemap import SitemapCheck
from app.checks.web.web_sri import SRICheck
from app.checks.web.web_ssrf_indicator import SSRFIndicatorCheck
from app.checks.web.web_vcs_exposure import VCSExposureCheck
from app.checks.web.web_waf_detection import WAFDetectionCheck
from app.checks.web.web_webdav import WebDAVCheck

__all__ = [
    "HeaderAnalysisCheck",
    "RobotsTxtCheck",
    "PathProbeCheck",
    "CorsCheck",
    "OpenAPICheck",
    "WebDAVCheck",
    "VCSExposureCheck",
    "ConfigExposureCheck",
    "DirectoryListingCheck",
    "DefaultCredsCheck",
    "DebugEndpointCheck",
    "CookieSecurityCheck",
    "AuthDetectionCheck",
    "WAFDetectionCheck",
    "SitemapCheck",
    "RedirectChainCheck",
    "ErrorPageCheck",
    "SSRFIndicatorCheck",
    "FaviconCheck",
    "HTTP2DetectionCheck",
    "HSTSPreloadCheck",
    "SRICheck",
    "MassAssignmentCheck",
]
