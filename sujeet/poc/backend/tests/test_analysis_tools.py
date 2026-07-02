"""Unit tests for analysis tools and OpenAI integration (mocked)."""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from agent_core import AgentState
from tools import analysis_tools as at


@pytest.fixture
def screened_state(sample_paper):
    state = AgentState("analysis test")
    paper = dict(sample_paper)
    paper["screening_decision"] = "INCLUDE"
    state.papers_found = [paper]
    return state


class TestCallLlm:
    def test_rule_based_fallback_without_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        assert at._call_llm("test prompt") == "RULE_BASED"

    @patch("openai.OpenAI")
    def test_openai_called_when_key_set(self, mock_openai_cls, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")

        mock_client = MagicMock()
        mock_openai_cls.return_value = mock_client
        mock_client.chat.completions.create.return_value = MagicMock(
            choices=[MagicMock(message=MagicMock(content="INCLUDE\nMeets PICO criteria."))]
        )

        result = at._call_llm("Screen this abstract")
        assert "INCLUDE" in result
        mock_client.chat.completions.create.assert_called_once()
        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["model"] == "gpt-4o-mini"

    @patch("openai.OpenAI")
    def test_openai_error_returns_llm_error_prefix(self, mock_openai_cls, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        mock_openai_cls.return_value.chat.completions.create.side_effect = RuntimeError("quota exceeded")

        result = at._call_llm("prompt")
        assert result.startswith("LLM_ERROR:")


class TestSlrScreen:
    def test_rule_based_screening_includes_relevant_paper(self, monkeypatch, sample_paper):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        state = AgentState("slr")
        state.papers_found = [dict(sample_paper)]

        result = at.slr_screen(
            criteria={
                "population": "ovarian cancer",
                "intervention": "niraparib",
                "outcome": "PFS",
                "study_design": "real world",
            },
            _state=state,
        )

        assert "SLR screening complete" in result
        assert state.papers_found[0]["screening_decision"] in ("INCLUDE", "EXCLUDE", "UNCERTAIN")

    @patch("tools.analysis_tools._call_llm")
    def test_llm_screening_parses_include(self, mock_llm, sample_paper):
        mock_llm.return_value = "INCLUDE\nStrong RWE match."
        state = AgentState("slr")
        state.papers_found = [dict(sample_paper)]

        at.slr_screen(criteria={"population": "x"}, _state=state)
        assert state.papers_found[0]["screening_decision"] == "INCLUDE"


class TestExtractEvidence:
    def test_rule_based_extraction_finds_pfs_and_n(self, monkeypatch, screened_state):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        result = at.extract_evidence(_state=screened_state)
        assert "Evidence extracted" in result
        assert len(screened_state.evidence_rows) == 1
        row = screened_state.evidence_rows[0]
        assert row["pfs_months"] == pytest.approx(8.5)
        assert row["n_patients"] == 240

    @patch("tools.analysis_tools._call_llm")
    def test_llm_json_extraction(self, mock_llm, screened_state):
        mock_llm.return_value = json.dumps({
            "n_patients": 120,
            "drug": "Niraparib",
            "comparator": "Olaparib",
            "pfs_months": 9.1,
            "os_months": 20.0,
            "study_design": "Retrospective",
            "country": "US",
        })

        at.extract_evidence(_state=screened_state)
        row = screened_state.evidence_rows[0]
        assert row["n_patients"] == 120
        assert row["drug"] == "Niraparib"


class TestGapAnalysis:
    def test_gap_analysis_marks_missing_sections(self, screened_state):
        screened_state.evidence_rows = [{
            "pfs_months": 8.5,
            "os_months": None,
            "country": "United States",
            "title": "niraparib study",
        }]

        result = at.gap_analysis(
            required_sections=[
                "US real-world PFS data",
                "EU real-world OS data",
                "Elderly patient subgroup (65+)",
            ],
            _state=screened_state,
        )

        assert "Gap analysis complete" in result
        assert len(screened_state.gaps) == 3
        statuses = {g["required_section"]: g["status"] for g in screened_state.gaps}
        assert statuses["US real-world PFS data"] == "COVERED"
        assert statuses["Elderly patient subgroup (65+)"] == "GAP"


class TestHcpScore:
    def test_hcp_score_ranks_frequent_authors(self, screened_state):
        screened_state.papers_found[0]["authors"] = ["Smith J", "Jones A"]

        result = at.hcp_score(top_n=5, _state=screened_state)
        assert "KOL scoring complete" in result
        assert len(screened_state.hcp_scores) >= 1
        assert screened_state.hcp_scores[0]["name"] == "Smith J"


class TestGenerateReport:
    def test_generate_report_writes_json(self, screened_state, temp_output_dir, monkeypatch):
        monkeypatch.setattr(at, "OUTPUT_DIR", temp_output_dir)
        screened_state.evidence_rows = [{"pmid": "1"}]
        screened_state.gaps = [{"status": "GAP"}]
        screened_state.hcp_scores = [{"priority": "HIGH"}]

        result = at.generate_report(_state=screened_state)
        assert "Report generated" in result
        assert "Saved to" in result

        files = [f for f in os.listdir(temp_output_dir) if f.startswith("evidence_report")]
        assert len(files) == 1
