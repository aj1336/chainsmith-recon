"""Co-located tests (Phase 56 §3) — split from test_rag_injection_vectors.py."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.rag.rag_chunk_boundary import RAGChunkBoundaryCheck
from app.checks.rag.rag_chunk_boundary.check import CANARY
from app.lib.http import HttpResponse


@pytest.fixture
def sample_service():
    return Service(
        url="http://rag.example.com:8080",
        host="rag.example.com",
        port=8080,
        scheme="http",
        service_type="ai",
    )


@pytest.fixture
def rag_context(sample_service):
    """Context with RAG endpoints and vector stores discovered."""
    return {
        "rag_endpoints": [
            {
                "url": "http://rag.example.com:8080/query",
                "path": "/query",
                "method": "POST",
                "indicators": ["field:sources"],
                "auth_required": False,
                "service": sample_service.to_dict(),
                "endpoint_type": "rag_query",
            },
            {
                "url": "http://rag.example.com:8080/api/v1/collections",
                "path": "/api/v1/collections",
                "store_type": "chroma",
                "status_code": 200,
                "auth_required": False,
                "service": sample_service.to_dict(),
                "endpoint_type": "vector_store",
            },
        ],
        "vector_stores": ["chroma"],
    }


@pytest.fixture
def ingestion_context(rag_context):
    """Context with writable ingestion endpoints."""
    ctx = dict(rag_context)
    ctx["ingestion_endpoints"] = [
        {
            "path": "/api/documents",
            "format": "json",
            "status": 201,
            "writable": True,
            "auth_required": False,
            "canary_id": "chainsmith-canary-test",
        },
    ]
    return ctx


def make_response(
    status_code: int = 200,
    headers: dict = None,
    body: str = "",
    error: str = None,
) -> HttpResponse:
    return HttpResponse(
        url="http://rag.example.com:8080",
        status_code=status_code,
        headers=headers or {},
        body=body,
        error=error,
        elapsed_ms=50.0,
    )


def _mock_client(get_fn=None, post_fn=None, delete_fn=None, options_fn=None):
    """Create mock async HTTP client."""
    client = AsyncMock()
    client.get = get_fn or AsyncMock(return_value=make_response(status_code=404))
    client.post = post_fn or AsyncMock(return_value=make_response(status_code=404))
    client.delete = delete_fn or AsyncMock(return_value=make_response(status_code=204))
    client.options = options_fn or AsyncMock(return_value=make_response(status_code=404))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock()
    return client


class TestChunkBoundary:
    @pytest.mark.asyncio
    async def test_bypass_confirmed_produces_high_observation(
        self, sample_service, ingestion_context
    ):
        """When the canary appears in a realistic response body, a high-severity
        observation with the correct title pattern is emitted."""
        check = RAGChunkBoundaryCheck()
        ingestion_context["rag_endpoints"][0]["endpoint_type"] = "rag_query"

        async def mock_post(url, **kw):
            body = kw.get("json", {})
            if "/api/documents" in url:
                return make_response(
                    status_code=201,
                    body='{"status":"ok","ids":["chainsmith-chunk-256tok"]}',
                )
            if body.get("query") and "boundary" in body["query"].lower():
                # Realistic RAG response with the canary embedded in LLM output
                return make_response(
                    body=json.dumps(
                        {
                            "answer": (
                                "Based on the retrieved documents, the system says: "
                                f"{CANARY}. This appears in the context window."
                            ),
                            "sources": [{"id": "chainsmith-chunk-256tok", "score": 0.92}],
                        }
                    )
                )
            return make_response(status_code=404)

        client = _mock_client(post_fn=mock_post)

        with patch("app.checks.rag.rag_chunk_boundary.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, ingestion_context)

        assert result.success
        high = [o for o in result.observations if o.severity == "high"]
        assert len(high) >= 1
        assert "chunk boundary bypass" in high[0].title.lower()
        assert "reassembled" in high[0].title.lower()
        assert CANARY in high[0].evidence

    @pytest.mark.asyncio
    async def test_no_canary_means_not_effective(self, sample_service, ingestion_context):
        """When the canary does NOT appear in query responses, an info observation
        is produced and no high/medium observations exist."""
        check = RAGChunkBoundaryCheck()
        ingestion_context["rag_endpoints"][0]["endpoint_type"] = "rag_query"

        async def mock_post(url, **kw):
            if "/api/documents" in url:
                return make_response(
                    status_code=201,
                    body='{"status":"ok","ids":["chainsmith-chunk-256tok"]}',
                )
            # Response that contains the topic but NOT the canary
            return make_response(
                body=json.dumps(
                    {
                        "answer": "Here is some general information about the topic.",
                        "sources": [{"id": "unrelated-doc", "score": 0.4}],
                    }
                )
            )

        client = _mock_client(post_fn=mock_post)

        with patch("app.checks.rag.rag_chunk_boundary.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, ingestion_context)

        assert result.success
        high = [o for o in result.observations if o.severity == "high"]
        assert len(high) == 0
        info = [o for o in result.observations if o.severity == "info"]
        assert len(info) >= 1
        assert "not effective" in info[0].title.lower()

    @pytest.mark.asyncio
    async def test_ingestion_failure_skips_quietly(self, sample_service, ingestion_context):
        """If the ingestion endpoint rejects the document (e.g. 403), no bypass
        observation is created."""
        check = RAGChunkBoundaryCheck()
        ingestion_context["rag_endpoints"][0]["endpoint_type"] = "rag_query"

        async def mock_post(url, **kw):
            if "/api/documents" in url:
                return make_response(status_code=403, body='{"error":"forbidden"}')
            return make_response(status_code=404)

        client = _mock_client(post_fn=mock_post)

        with patch("app.checks.rag.rag_chunk_boundary.check.AsyncHttpClient", return_value=client):
            result = await check.check_service(sample_service, ingestion_context)

        assert result.success
        high = [o for o in result.observations if o.severity == "high"]
        assert len(high) == 0
