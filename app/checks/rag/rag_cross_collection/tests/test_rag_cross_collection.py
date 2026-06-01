"""Co-located tests (Phase 56 §3) — split from test_rag_retrieval.py."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.checks.base import Service
from app.checks.rag.rag_cross_collection import RAGCrossCollectionCheck
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
def accessible_store_context(rag_context):
    """Context with accessible vector stores."""
    ctx = dict(rag_context)
    ctx["accessible_stores"] = [
        {
            "store_type": "chroma",
            "accessible_ops": [
                {"operation": "list_collections", "path": "/api/v1/collections", "status": 200},
                {
                    "operation": "dump_documents",
                    "path": "/api/v1/collections/docs/get",
                    "status": 200,
                },
            ],
            "collections": ["docs", "hr_policies", "faq"],
            "doc_count": 150,
        },
    ]
    return ctx


@pytest.fixture
def kb_structure_context(accessible_store_context):
    """Context with knowledge base structure."""
    ctx = dict(accessible_store_context)
    ctx["knowledge_base_structure"] = [
        {
            "store_type": "chroma",
            "collection_count": 3,
            "total_documents": 150,
            "collections": [
                {
                    "name": "docs",
                    "doc_count": 80,
                    "dimensions": 1536,
                    "metadata_fields": ["source", "author"],
                },
                {
                    "name": "hr_policies",
                    "doc_count": 50,
                    "dimensions": 1536,
                    "metadata_fields": ["source"],
                },
                {"name": "faq", "doc_count": 20, "dimensions": 1536, "metadata_fields": []},
            ],
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


class TestCrossCollection:
    def test_metadata(self):
        check = RAGCrossCollectionCheck()
        assert check.name == "rag_cross_collection"
        assert "cross_collection_results" in check.produces

    @pytest.mark.asyncio
    async def test_isolation_violated(self, sample_service, kb_structure_context):
        check = RAGCrossCollectionCheck()

        async def mock_post(url, **kw):
            # Query to docs collection returns content mentioning hr_policies
            if "docs" in url:
                return make_response(
                    body=json.dumps(
                        {
                            "ids": [["hr1"]],
                            "documents": [["hr_policies content leaked"]],
                        }
                    )
                )
            return make_response(status_code=404)

        client = _mock_client(post_fn=mock_post)

        with patch(
            "app.checks.rag.rag_cross_collection.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, kb_structure_context)

        assert result.success
        # Should detect cross-collection leak
        leak_observations = [f for f in result.observations if f.severity in ("critical", "high")]
        assert len(leak_observations) >= 1

    @pytest.mark.asyncio
    async def test_isolation_enforced(self, sample_service, kb_structure_context):
        check = RAGCrossCollectionCheck()

        async def mock_post(url, **kw):
            if "docs" in url:
                return make_response(
                    body=json.dumps(
                        {
                            "ids": [["d1"]],
                            "documents": [["Only docs content here"]],
                        }
                    )
                )
            return make_response(status_code=404)

        client = _mock_client(post_fn=mock_post)

        with patch(
            "app.checks.rag.rag_cross_collection.check.AsyncHttpClient", return_value=client
        ):
            result = await check.check_service(sample_service, kb_structure_context)

        assert result.success
        info = [f for f in result.observations if f.severity == "info"]
        assert len(info) >= 1
