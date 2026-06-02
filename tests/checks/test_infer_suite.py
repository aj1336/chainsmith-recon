"""Contract for `infer_suite` after the Phase 56.7 collapse (§14.4).

Every check name is now uniformly `<suite>_<name>`, so suite inference is a
pure prefix split: the first `_`-delimited token, validated against the seven
known suites, else `"other"`. These tests lock that contract so a future change
can't silently reintroduce the old substring/`_MCP_CHECK_NAMES` guessing.
"""

import pytest

from app.check_resolver import infer_suite


class TestInferSuitePrefixSplit:
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("network_dns_enumeration", "network"),
            ("web_robots_txt", "web"),
            ("ai_jailbreak_testing", "ai"),
            ("mcp_auth_check", "mcp"),  # mcp_ restored in 56.7
            ("agent_discovery", "agent"),
            ("rag_chunk_boundary", "rag"),
            ("cag_cache_poisoning", "cag"),
        ],
    )
    def test_known_prefix_routes_to_its_suite(self, name, expected):
        assert infer_suite(name) == expected

    def test_unknown_prefix_routes_to_other(self):
        assert infer_suite("totally_unknown_check") == "other"

    def test_no_underscore_routes_to_other(self):
        # A bare single-token name has no suite prefix.
        assert infer_suite("favicon") == "other"

    def test_split_is_first_token_only(self):
        # A suite word appearing *after* the first token must NOT match — the
        # old substring fallback would have mis-grabbed this; the prefix split
        # must not.
        assert infer_suite("other_network_thing") == "other"

    @pytest.mark.parametrize(
        "legacy_bare_name",
        [
            "auth_check",  # ex-stripped MCP name (56.5) — no longer special-cased
            "discovery",
            "jailbreak_testing",  # pre-56.7 AI name
            "cors",  # pre-56.2 web name
        ],
    )
    def test_legacy_bare_names_no_longer_guessed(self, legacy_bare_name):
        # These used to route via `_MCP_CHECK_NAMES` / the substring map. After
        # the collapse they have no known prefix and route to "other". They never
        # reach infer_suite at runtime (sims carry an explicit suite; bare-emulated
        # sims don't match any real check and are dropped), so this is the intended
        # post-collapse behavior, not a regression.
        assert infer_suite(legacy_bare_name) == "other"

    def test_case_insensitive_prefix(self):
        assert infer_suite("NETWORK_dns_enumeration") == "network"
