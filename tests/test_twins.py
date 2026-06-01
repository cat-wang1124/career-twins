"""
Tests for backend.twins.

We mock the Exa client entirely so tests are deterministic, fast, and don't
burn API credits. Run with:  pytest -v
"""

from __future__ import annotations

import os
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest


# Set a dummy key BEFORE importing backend.twins so its _exa_client doesn't fail
os.environ.setdefault("EXA_API_KEY", "test-key")

from backend import twins as tw  # noqa: E402


# ----------- helpers -----------

def fake_candidate(name="Some Person", company="Acme", role="Engineer"):
    return SimpleNamespace(
        url=f"https://linkedin.com/in/{name.lower().replace(' ', '-')}",
        title=f"{name} - {role} - {company} | LinkedIn",
        highlights=[f"Works on cool things at {company}.", "Likes Rust."],
        score=0.85,
    )


def fake_exa(candidates=None, summary_text="Strong overlap in systems work."):
    """Return a MagicMock Exa client with the methods we use."""
    candidates = candidates or [fake_candidate(f"Person {i}") for i in range(3)]
    exa = MagicMock()
    exa.find_similar_and_contents.return_value = SimpleNamespace(results=candidates)
    exa.search_and_contents.return_value = SimpleNamespace(results=candidates)

    # /contents returns a list with a summary
    contents_result = SimpleNamespace(
        results=[SimpleNamespace(summary=summary_text)]
    )
    exa.get_contents.return_value = contents_result

    # personal-site search returns one result
    exa.search.return_value = SimpleNamespace(
        results=[SimpleNamespace(url="https://blog.example.com")]
    )
    return exa


@pytest.fixture(autouse=True)
def clear_cache(tmp_path, monkeypatch):
    """Point cache at a temp dir so tests don't pollute the real cache."""
    monkeypatch.setattr(tw, "CACHE_PATH", tmp_path / "cache.json")
    yield


# ----------- parsing tests -----------

def test_is_linkedin_url():
    assert tw._is_linkedin_url("https://www.linkedin.com/in/abc/")
    assert tw._is_linkedin_url("HTTPS://LINKEDIN.COM/IN/XYZ")
    assert not tw._is_linkedin_url("https://example.com/abc")
    assert not tw._is_linkedin_url("not a url")


def test_looks_like_resume():
    short = "Jane Doe, engineer."
    long_multiline = "Jane Doe\n" + ("Senior engineer with experience in X. " * 20)
    long_singleline = "Senior engineer with experience in X. " * 20  # no newlines
    assert not tw._looks_like_resume(short)
    assert tw._looks_like_resume(long_multiline)
    assert not tw._looks_like_resume(long_singleline)


def test_parse_name_handles_various_separators():
    assert tw._parse_name("Catherine Wang - SWE - Microsoft | LinkedIn") == "Catherine Wang"
    assert tw._parse_name("Some Person · CTO · Startup") == "Some Person"
    assert tw._parse_name(None) == "Unknown"
    assert tw._parse_name("") == "Unknown"


def test_parse_current_role():
    title = "Catherine Wang - Software Engineer II - Microsoft | LinkedIn"
    assert tw._parse_current_role(title) == "Software Engineer II at Microsoft"

    short_title = "Just a Name | LinkedIn"
    assert tw._parse_current_role(short_title) is None


# ----------- find_twins integration tests -----------

def test_find_twins_with_url(monkeypatch):
    exa = fake_exa()
    monkeypatch.setattr(tw, "_exa_client", lambda: exa)

    result = tw.find_twins("https://linkedin.com/in/test", num_twins=3, use_cache=False)

    assert result.query_kind == "linkedin_url"
    assert len(result.twins) == 3
    assert result.from_cache is False
    assert exa.find_similar_and_contents.called
    assert not exa.search_and_contents.called  # text path not taken


def test_find_twins_with_resume_text(monkeypatch):
    exa = fake_exa()
    monkeypatch.setattr(tw, "_exa_client", lambda: exa)

    resume = "Catherine Wang\n" + ("Senior SWE working on Windows Shell and search. " * 8)
    result = tw.find_twins(resume, num_twins=3, use_cache=False)

    assert result.query_kind == "resume_text"
    assert len(result.twins) == 3
    assert exa.search_and_contents.called
    assert not exa.find_similar_and_contents.called


def test_find_twins_rejects_garbage_input(monkeypatch):
    monkeypatch.setattr(tw, "_exa_client", lambda: fake_exa())
    with pytest.raises(ValueError):
        tw.find_twins("just a short string", num_twins=3, use_cache=False)


def test_find_twins_enriches_with_why_match(monkeypatch):
    exa = fake_exa(summary_text="Both have deep Windows shell experience.")
    monkeypatch.setattr(tw, "_exa_client", lambda: exa)

    result = tw.find_twins("https://linkedin.com/in/test", num_twins=2, use_cache=False)

    for twin in result.twins:
        assert twin.why_match == "Both have deep Windows shell experience."
        assert twin.personal_site == "https://blog.example.com"


def test_find_twins_caches_results(monkeypatch):
    exa = fake_exa()
    monkeypatch.setattr(tw, "_exa_client", lambda: exa)

    # First call: not cached
    r1 = tw.find_twins("https://linkedin.com/in/test", num_twins=2, use_cache=True)
    assert r1.from_cache is False

    # Second call with same args: should hit cache, not the API
    exa.find_similar_and_contents.reset_mock()
    r2 = tw.find_twins("https://linkedin.com/in/test", num_twins=2, use_cache=True)
    assert r2.from_cache is True
    assert not exa.find_similar_and_contents.called


def test_find_twins_caps_at_max(monkeypatch):
    exa = fake_exa(candidates=[fake_candidate(f"P{i}") for i in range(50)])
    monkeypatch.setattr(tw, "_exa_client", lambda: exa)

    result = tw.find_twins(
        "https://linkedin.com/in/test",
        num_twins=100,  # over max
        use_cache=False,
    )
    # Should have been capped to MAX_NUM_TWINS in the request
    _, kwargs = exa.find_similar_and_contents.call_args
    assert kwargs["num_results"] == tw.MAX_NUM_TWINS


def test_enrichment_failures_dont_kill_request(monkeypatch):
    """If the per-candidate enrichment raises, we should still get a twin back."""
    exa = fake_exa()
    exa.get_contents.side_effect = RuntimeError("transient API error")
    exa.search.side_effect = RuntimeError("transient API error")
    monkeypatch.setattr(tw, "_exa_client", lambda: exa)

    result = tw.find_twins("https://linkedin.com/in/test", num_twins=3, use_cache=False)

    # All twins should still be returned, just without enrichment
    assert len(result.twins) == 3
    for twin in result.twins:
        assert twin.why_match is None
        assert twin.personal_site is None


def test_to_dict_is_json_serializable(monkeypatch):
    import json
    exa = fake_exa()
    monkeypatch.setattr(tw, "_exa_client", lambda: exa)

    result = tw.find_twins("https://linkedin.com/in/test", num_twins=2, use_cache=False)
    payload = tw.to_dict(result)
    # Should not raise
    json.dumps(payload)
