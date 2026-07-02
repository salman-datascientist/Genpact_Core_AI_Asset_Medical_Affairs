"""Shared pytest fixtures for Medical Affairs POC tests."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

POC_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = POC_ROOT / "backend"
FRONTEND_DIR = POC_ROOT / "frontend"


@pytest.fixture(scope="session")
def poc_root() -> Path:
    return POC_ROOT


@pytest.fixture(scope="session")
def backend_dir() -> Path:
    return BACKEND_DIR


@pytest.fixture(scope="session")
def frontend_dir() -> Path:
    return FRONTEND_DIR


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    """Prevent tests from using real API keys unless integration tests run."""
    monkeypatch.delenv("PUBMED_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture
def temp_db_path(tmp_path):
    return str(tmp_path / "test_papers.db")


@pytest.fixture
def temp_output_dir(tmp_path):
    path = tmp_path / "outputs"
    path.mkdir()
    return str(path)


@pytest.fixture
def sample_paper():
    return {
        "pmid": "12345678",
        "title": "Real-world niraparib outcomes in ovarian cancer",
        "authors": ["Smith J", "Jones A"],
        "journal": "Journal of Oncology",
        "pub_year": "2022",
        "doi": "10.1000/test.123",
        "country": "United States",
        "pub_types": ["Journal Article"],
        "mesh_terms": ["Ovarian Neoplasms"],
        "keywords": ["niraparib", "real world"],
        "abstract": (
            "Retrospective cohort of n=240 patients. "
            "Median PFS was 8.5 months and overall survival 22.3 months "
            "with niraparib vs olaparib comparator."
        ),
        "embed_text": "stub",
        "fetched_at": "2026-01-01T00:00:00",
        "_fetched": True,
        "_label": "RWE_search",
    }


@pytest.fixture
def agent_state(sample_paper):
    from agent_core import AgentState

    state = AgentState(task="Test evidence task")
    state.papers_found.append(dict(sample_paper))
    return state


@pytest.fixture
def api_client(monkeypatch, temp_db_path, temp_output_dir):
    if str(BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(BACKEND_DIR))

    import api_server as server

    monkeypatch.setattr(server, "DB_PATH", temp_db_path)
    monkeypatch.setattr(server, "OUTPUT_DIR", temp_output_dir)
    monkeypatch.setattr(server, "DATA_DIR", str(Path(temp_db_path).parent))

    server.agent_status = {
        "running": False,
        "steps": [],
        "progress": 0,
        "task": "",
        "started_at": None,
        "done": False,
        "error": None,
        "result": None,
        "pubmed_rate": None,
    }

    from fastapi.testclient import TestClient

    with TestClient(server.app) as client:
        yield client, server


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
