"""
Optional live integration tests for PubMed and OpenAI APIs.

Skipped by default. Run with:
  RUN_INTEGRATION=1 pytest -m integration backend/tests/test_integration_apis.py
"""

import os

import pytest

pytestmark = pytest.mark.integration


def _integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION", "").strip() == "1"


@pytest.fixture(autouse=True)
def _require_integration_flag():
    if not _integration_enabled():
        pytest.skip("Set RUN_INTEGRATION=1 to run live API integration tests")


class TestLivePubMed:
    def test_esearch_returns_pmids(self, monkeypatch):
        from dotenv import load_dotenv
        from pathlib import Path

        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        monkeypatch.setenv("PUBMED_API_KEY", os.getenv("PUBMED_API_KEY", ""))

        from tools import pubmed_tools as pt
        from tools.pubmed_rate_limiter import configure_rate_limit

        configure_rate_limit("with_api_key" if os.getenv("PUBMED_API_KEY") else "no_api_key", 2, bool(os.getenv("PUBMED_API_KEY")))

        state = __import__("agent_core").AgentState("live pubmed")
        result = pt.pubmed_search(
            query="niraparib ovarian cancer",
            max_results=3,
            label="live_test",
            _state=state,
        )
        assert "ERROR" not in result
        assert len(state.papers_found) >= 1


class TestLiveOpenAI:
    def test_openai_chat_completion(self, monkeypatch):
        from dotenv import load_dotenv
        from pathlib import Path

        load_dotenv(Path(__file__).resolve().parents[1] / ".env")
        key = os.getenv("OPENAI_API_KEY", "")
        if not key:
            pytest.skip("OPENAI_API_KEY not set in .env")

        from tools.analysis_tools import _call_llm

        result = _call_llm("Reply with exactly: OK", max_tokens=10)
        assert result != "RULE_BASED"
        assert not result.startswith("LLM_ERROR:")
        assert "OK" in result.upper()
