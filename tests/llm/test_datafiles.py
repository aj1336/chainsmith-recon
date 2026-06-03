"""
Tests for app/lib/datafiles.py - externalized check-data loader (Phase 56.13).

Covers the two fallback-first loaders against both the real shipped data files
and synthetic missing/empty/unparseable cases (via a monkeypatched DATA_ROOT).
"""

import pytest

from app.lib import datafiles
from app.lib.datafiles import load_data, load_wordlist

pytestmark = pytest.mark.unit


# ── Happy path against the real shipped app/data files ──────────────


def test_load_real_wordlist():
    entries = load_wordlist("wordlists/subdomains.txt", ["fallback"])
    assert "www" in entries and "api" in entries
    assert entries != ["fallback"]
    assert all(not e.startswith("#") and e.strip() for e in entries)


def test_load_real_endpoint_yaml():
    paths = load_data("endpoints/chat_paths.yaml", ["fb"])
    assert isinstance(paths, list)
    assert "/v1/chat/completions" in paths


def test_load_real_payload_yaml_structure():
    data = load_data("payloads/agent_goal_injection.yaml", {})
    assert set(data) == {"fallback", "framework"}
    assert isinstance(data["fallback"], list)


# ── Fallback behavior (synthetic DATA_ROOT) ─────────────────────────


def test_wordlist_missing_file_returns_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(datafiles, "DATA_ROOT", tmp_path)
    assert load_wordlist("nope.txt", ["a", "b"]) == ["a", "b"]


def test_wordlist_skips_blanks_and_comments(tmp_path, monkeypatch):
    monkeypatch.setattr(datafiles, "DATA_ROOT", tmp_path)
    (tmp_path / "w.txt").write_text("# header\n\nalpha\n  beta  \n# c\ngamma\n", encoding="utf-8")
    assert load_wordlist("w.txt", ["fb"]) == ["alpha", "beta", "gamma"]


def test_wordlist_empty_file_returns_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(datafiles, "DATA_ROOT", tmp_path)
    (tmp_path / "w.txt").write_text("# only comments\n\n", encoding="utf-8")
    assert load_wordlist("w.txt", ["fb"]) == ["fb"]


def test_data_missing_file_returns_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(datafiles, "DATA_ROOT", tmp_path)
    assert load_data("nope.yaml", {"k": 1}) == {"k": 1}


def test_data_empty_file_returns_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(datafiles, "DATA_ROOT", tmp_path)
    (tmp_path / "d.yaml").write_text("", encoding="utf-8")
    assert load_data("d.yaml", ["fb"]) == ["fb"]


def test_data_unparseable_returns_fallback(tmp_path, monkeypatch):
    monkeypatch.setattr(datafiles, "DATA_ROOT", tmp_path)
    (tmp_path / "d.yaml").write_text("key: [unclosed\n", encoding="utf-8")
    assert load_data("d.yaml", ["fb"]) == ["fb"]


def test_data_pairs_unpack_like_tuples(tmp_path, monkeypatch):
    """A YAML sequence of 2-item pairs unpacks exactly like the tuple literals."""
    monkeypatch.setattr(datafiles, "DATA_ROOT", tmp_path)
    (tmp_path / "p.yaml").write_text("- [cat, msg]\n- [cat2, msg2]\n", encoding="utf-8")
    loaded = load_data("p.yaml", [])
    pairs = [(c, m) for c, m in loaded]
    assert pairs == [("cat", "msg"), ("cat2", "msg2")]
