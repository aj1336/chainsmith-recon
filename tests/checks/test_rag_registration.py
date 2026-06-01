"""Cross-cutting registration tests for the rag suite."""


class TestCheckResolverRegistration:
    def test_all_rag_checks_registered(self):
        """Every expected RAG check name appears in the resolver output."""
        from app.check_resolver import get_real_checks

        checks = get_real_checks()
        check_names = {c.name for c in checks}

        expected_rag_checks = [
            "rag_discovery",
            "rag_vector_store_access",
            "rag_auth_bypass",
            "rag_collection_enumeration",
            "rag_embedding_fingerprint",
            "rag_indirect_injection",
            "rag_document_exfiltration",
            "rag_retrieval_manipulation",
            "rag_source_attribution",
            "rag_cache_poisoning",
            "rag_corpus_poisoning",
            "rag_metadata_injection",
            "rag_chunk_boundary",
            "rag_multimodal_injection",
            "rag_fusion_reranker",
            "rag_cross_collection",
            "rag_adversarial_embedding",
        ]

        for name in expected_rag_checks:
            assert name in check_names, f"RAG check '{name}' not registered"

    def test_rag_suite_filter_returns_only_rag_checks(self):
        """resolve_checks(suites=['rag']) returns checks whose names all
        start with 'rag_' and includes the three checks under test."""
        from app.check_resolver import resolve_checks

        checks = resolve_checks(suites=["rag"])
        assert len(checks) > 0
        assert all(c.name.startswith("rag_") for c in checks)
        names = {c.name for c in checks}
        assert "rag_chunk_boundary" in names
        assert "rag_multimodal_injection" in names
        assert "rag_adversarial_embedding" in names
