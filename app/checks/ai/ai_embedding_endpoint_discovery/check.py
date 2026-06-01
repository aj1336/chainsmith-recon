"""
app/checks/ai/endpoints.py - AI Endpoint Discovery

Find chat/completion and embedding endpoints on services.
"""

from typing import Any

from app.checks.base import CheckCondition, CheckResult, Service, ServiceIteratingCheck
from app.lib.ai_helpers import fmt_endpoint_probe_evidence
from app.lib.http import AsyncHttpClient, HttpConfig
from app.lib.observations import build_observation


class EmbeddingEndpointCheck(ServiceIteratingCheck):
    """Discover embedding and vector endpoints."""

    name = "ai_embedding_endpoint_discovery"
    description = "Find embedding and vector endpoints on AI services"

    conditions = [CheckCondition("services", "truthy"), CheckCondition("services_probed", "truthy")]
    produces = ["embedding_endpoints"]
    service_types = ["ai", "api", "http"]

    reason = "Embedding endpoints may leak training data or enable inference attacks"
    references = ["OWASP LLM Top 10 - LLM06 Sensitive Information Disclosure"]
    techniques = ["endpoint discovery", "embedding extraction"]

    EMBEDDING_PATHS = [
        "/v1/embeddings",
        "/embeddings",
        "/api/embeddings",
        "/api/embed",
        "/embed",
        "/encode",
        "/api/encode",
        "/api/vectors",
        "/vectors",
        "/similarity",
        "/search",
        "/api/search",
        "/feature-extraction",
    ]

    async def check_service(self, service: Service, context: dict[str, Any]) -> CheckResult:
        result = CheckResult(success=True)
        embedding_endpoints = []

        cfg = HttpConfig(timeout_seconds=10.0, verify_ssl=False)
        try:
            async with AsyncHttpClient(cfg) as client:
                for path in self.EMBEDDING_PATHS:
                    url = service.with_path(path)

                    resp = await client.post(
                        url,
                        json={"input": "test"},
                        headers={"Content-Type": "application/json"},
                    )

                    if resp.error or resp.status_code in (404, 405):
                        continue

                    result.observations.append(
                        build_observation(
                            check_name=self.name,
                            title=f"Embedding endpoint: {path}",
                            description="Embedding/vector endpoint discovered",
                            severity="info",
                            evidence=fmt_endpoint_probe_evidence(path, resp.status_code),
                            host=service.host,
                            discriminator=f"embed-{path.strip('/').replace('/', '-')}",
                            target=service,
                            target_url=url,
                        )
                    )

                    embedding_endpoints.append(
                        {
                            "url": url,
                            "path": path,
                            "service": service.to_dict(),
                        }
                    )

        except Exception as e:
            result.errors.append(f"{service.url}: {e}")

        if embedding_endpoints:
            result.outputs["embedding_endpoints"] = embedding_endpoints

        return result
