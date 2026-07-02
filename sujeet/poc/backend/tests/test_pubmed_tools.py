"""Unit tests for PubMed tools (mocked HTTP — no live NCBI calls)."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest
import xmltodict

from agent_core import AgentState
from tools import pubmed_tools as pt

SAMPLE_ESEARCH_JSON = {
    "esearchresult": {
        "idlist": ["11111111", "22222222"],
        "count": "2",
    }
}

SAMPLE_PUBMED_XML = """<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation Status="MEDLINE">
      <PMID Version="1">11111111</PMID>
      <Article>
        <ArticleTitle>Real world niraparib study</ArticleTitle>
        <Abstract>
          <AbstractText>Observational cohort n=100. PFS 10.2 months.</AbstractText>
        </Abstract>
        <AuthorList>
          <Author><LastName>Smith</LastName><Initials>J</Initials></Author>
        </AuthorList>
        <Journal>
          <Title>Oncology Journal</Title>
          <JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue>
        </Journal>
        <PublicationTypeList>
          <PublicationType>Journal Article</PublicationType>
        </PublicationTypeList>
      </Article>
      <MeshHeadingList>
        <MeshHeading><DescriptorName>Ovarian Neoplasms</DescriptorName></MeshHeading>
      </MeshHeadingList>
      <MedlineJournalInfo><Country>United States</Country></MedlineJournalInfo>
    </MedlineCitation>
    <PubmedData>
      <ArticleIdList>
        <ArticleId IdType="doi">10.1000/test.111</ArticleId>
      </ArticleIdList>
    </PubmedData>
  </PubmedArticle>
</PubmedArticleSet>
"""


class TestPubmedSearch:
    @patch("tools.pubmed_tools.eutils_get")
    def test_search_stores_pmids_in_state(self, mock_get, temp_db_path):
        pt.DB_PATH = temp_db_path
        pt.PUBMED_API_KEY = "test-key"

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = SAMPLE_ESEARCH_JSON
        mock_get.return_value = mock_resp

        state = AgentState("search test")
        result = pt.pubmed_search(
            query="niraparib ovarian cancer",
            max_results=50,
            label="RWE_search",
            _state=state,
        )

        assert "Queued 2 PMIDs" in result
        assert len(state.papers_found) == 2
        assert state.papers_found[0]["pmid"] == "11111111"
        assert state.papers_found[0]["_fetched"] is False

    @patch("tools.pubmed_tools.eutils_get")
    def test_search_handles_rate_limit_error(self, mock_get, temp_db_path):
        from tools.pubmed_rate_limiter import PubMedRateLimitError

        pt.DB_PATH = temp_db_path
        mock_get.side_effect = PubMedRateLimitError("HTTP 429", status_code=429)

        result = pt.pubmed_search(query="test", _state=AgentState("x"))
        assert "ERROR pubmed_search" in result
        assert "rate limit" in result.lower()


class TestPubmedFetch:
    @patch("tools.pubmed_tools.eutils_get")
    def test_fetch_parses_xml_into_state(self, mock_get, temp_db_path):
        pt.DB_PATH = temp_db_path
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.text = SAMPLE_PUBMED_XML
        mock_get.return_value = mock_resp

        state = AgentState("fetch test")
        state.papers_found = [{"pmid": "11111111", "_fetched": False, "_label": "RWE"}]

        result = pt.pubmed_fetch(_state=state)
        assert "Fetched full metadata for 1 papers" in result
        assert state.papers_found[0]["_fetched"] is True
        assert "niraparib" in state.papers_found[0]["title"].lower()
        assert state.papers_found[0]["authors"] == ["Smith J"]

    def test_fetch_without_state_returns_error(self):
        assert "ERROR" in pt.pubmed_fetch(_state=None)

    def test_fetch_with_no_pending_pmids(self):
        state = AgentState("empty")
        state.papers_found = [{"pmid": "1", "_fetched": True}]
        assert "No new PMIDs" in pt.pubmed_fetch(_state=state)


class TestParseArticle:
    def test_parse_article_from_xml_dict(self):
        data = xmltodict.parse(SAMPLE_PUBMED_XML)
        article = data["PubmedArticleSet"]["PubmedArticle"]
        parsed = pt._parse_article(article)

        assert parsed["pmid"] == "11111111"
        assert parsed["pub_year"] == "2023"
        assert parsed["doi"] == "10.1000/test.111"
        assert parsed["country"] == "United States"


class TestSaveToDb:
    def test_save_to_db_inserts_papers(self, temp_db_path, sample_paper):
        pt.DB_PATH = temp_db_path
        state = AgentState("db test")
        state.papers_found = [sample_paper]

        result = pt.save_to_db(_state=state)
        assert "Saved 1 papers" in result

        conn = sqlite3.connect(temp_db_path)
        row = conn.execute("SELECT pmid, title FROM papers WHERE pmid = ?", ("12345678",)).fetchone()
        conn.close()
        assert row is not None
        assert "niraparib" in row[1].lower()

    def test_save_to_db_skips_unfetched(self, temp_db_path):
        pt.DB_PATH = temp_db_path
        state = AgentState("db test")
        state.papers_found = [{"pmid": "99", "_fetched": False}]
        assert "No fetched papers" in pt.save_to_db(_state=state)
