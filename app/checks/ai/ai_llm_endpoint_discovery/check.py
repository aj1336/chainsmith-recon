"""
app/checks/ai/endpoints.py - AI Endpoint Discovery

Find chat/completion and embedding endpoints on services.
"""

from typing import Any

from app.checks.base import CheckCondition, CheckResult, Service, ServiceIteratingCheck
from app.lib.ai_helpers import fmt_endpoint_probe_evidence
from app.lib.http import AsyncHttpClient, HttpConfig
from app.lib.observations import build_observation


class LLMEndpointCheck(ServiceIteratingCheck):
    """Discover LLM chat and completion endpoints."""

    name = "ai_llm_endpoint_discovery"
    description = "Find chat and completion endpoints on AI services"

    conditions = [CheckCondition("services", "truthy"), CheckCondition("services_probed", "truthy")]
    produces = ["chat_endpoints", "completion_endpoints"]
    service_types = ["ai", "api", "http"]

    reason = "Chat/completion endpoints are the primary interface for prompt injection and other AI attacks"
    references = ["OWASP LLM Top 10 - LLM01 Prompt Injection"]
    techniques = ["endpoint discovery", "API enumeration"]

    CHAT_PATHS = [
        "/v1/chat/completions",
        "/v1/completions",
        "/chat/completions",
        "/completions",
        "/v1/messages",
        "/messages",
        "/api/generate",
        "/api/chat",
        "/chat",
        "/inference",
        "/predict",
        "/api/inference",
        "/api/predict",
        "/invoke",
        "/stream",
        "/batch",
        "/generate",
        "/v1/generate",
        "/generate_stream",
    ]

    async def check_service(self, service: Service, context: dict[str, Any]) -> CheckResult:
        result = CheckResult(success=True)
        chat_endpoints = []

        cfg = HttpConfig(timeout_seconds=10.0, verify_ssl=False)
        try:
            async with AsyncHttpClient(cfg) as client:
                for path in self.CHAT_PATHS:
                    url = service.with_path(path)

                    opts = await client.options(url)
                    if opts.error or opts.status_code >= 500:
                        continue

                    post_resp = await client.post(
                        url,
                        json={"messages": [{"role": "user", "content": "test"}]},
                        headers={"Content-Type": "application/json"},
                    )

                    if post_resp.error or post_resp.status_code in (404, 405):
                        continue

                    api_format = self._detect_api_format(path)

                    result.observations.append(
                        build_observation(
                            check_name=self.name,
                            title=f"LLM endpoint: {path}",
                            description=f"Chat/completion endpoint discovered ({api_format} format)",
                            severity="info",
                            evidence=fmt_endpoint_probe_evidence(
                                path, post_resp.status_code, api_format
                            ),
                            host=service.host,
                            discriminator=f"chat-{path.strip('/').replace('/', '-')}",
                            target=service,
                            target_url=url,
                            raw_data={"api_format": api_format},
                        )
                    )

                    chat_endpoints.append(
                        {
                            "url": url,
                            "path": path,
                            "service": service.to_dict(),
                            "api_format": api_format,
                            "status_code": post_resp.status_code,
                        }
                    )

        except Exception as e:
            result.errors.append(f"{service.url}: {e}")

        if chat_endpoints:
            result.outputs["chat_endpoints"] = chat_endpoints

        return result

    def _detect_api_format(self, path: str) -> str:
        path_lower = path.lower()
        if "/v1/chat/completions" in path_lower or "/chat/completions" in path_lower:
            return "openai"
        elif "/messages" in path_lower:
            return "anthropic"
        elif "/api/generate" in path_lower or "/api/chat" in path_lower:
            return "ollama"
        elif "/invoke" in path_lower or "/stream" in path_lower:
            return "langserve"
        elif "generate" in path_lower:
            return "tgi"
        return "unknown"
