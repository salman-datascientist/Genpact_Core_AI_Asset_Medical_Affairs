"""Unit tests for FastAPI backend endpoints."""

from unittest.mock import MagicMock, patch


class TestHealthAndConfig:
    def test_health(self, api_client):
        client, _ = api_client
        resp = client.get("/api/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_pubmed_config_without_api_key(self, api_client, monkeypatch):
        client, _ = api_client
        monkeypatch.delenv("PUBMED_API_KEY", raising=False)

        resp = client.get("/api/pubmed-config")
        assert resp.status_code == 200
        data = resp.json()
        assert data["max_without_key"] == 3
        assert data["max_with_key"] == 10
        assert data["has_api_key"] is False
        assert "3 requests/second" in data["disclosure"]

    def test_pubmed_config_with_api_key(self, api_client, monkeypatch):
        client, _ = api_client
        monkeypatch.setenv("PUBMED_API_KEY", "test-ncbi-key")

        resp = client.get("/api/pubmed-config")
        data = resp.json()
        assert data["has_api_key"] is True
        assert data["default_tier"] == "with_api_key"


class TestRunAgent:
    def test_run_agent_validates_rate_limit(self, api_client):
        client, _ = api_client
        resp = client.post("/api/run-agent", json={
            "drug": "Niraparib",
            "pubmed_tier": "no_api_key",
            "pubmed_requests_per_second": 10,
        })
        assert resp.status_code == 400
        assert "cannot exceed 3" in resp.json()["error"]

    @patch("api_server.threading.Thread")
    @patch("api_server._run_agent_thread")
    def test_run_agent_starts_background_job(self, mock_run_fn, mock_thread_cls, api_client, monkeypatch):
        client, server = api_client
        monkeypatch.setenv("PUBMED_API_KEY", "test-key")
        mock_thread_cls.return_value.start = MagicMock()

        resp = client.post("/api/run-agent", json={
            "drug": "Niraparib",
            "indication": "Ovarian Cancer",
            "pubmed_tier": "with_api_key",
            "pubmed_requests_per_second": 5,
        })
        assert resp.status_code == 200
        assert resp.json()["message"] == "Agent started"
        assert server.agent_status["running"] is True
        assert server.agent_status["pubmed_rate"]["requests_per_second"] == 5
        mock_thread_cls.assert_called_once()
        mock_run_fn.assert_not_called()  # runs in thread, not inline

    def test_run_agent_rejects_when_already_running(self, api_client, monkeypatch):
        client, server = api_client
        server.agent_status["running"] = True
        monkeypatch.setenv("PUBMED_API_KEY", "test-key")

        resp = client.post("/api/run-agent", json={
            "pubmed_tier": "with_api_key",
            "pubmed_requests_per_second": 2,
        })
        assert resp.status_code == 409


class TestAgentStatusAndResults:
    def test_agent_status_idle(self, api_client):
        client, _ = api_client
        resp = client.get("/api/agent-status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["running"] is False
        assert data["done"] is False

    def test_results_latest_empty(self, api_client):
        client, _ = api_client
        resp = client.get("/api/results/latest")
        assert resp.status_code == 200
        assert "error" in resp.json()


class TestPapersEndpoint:
    def test_papers_empty_db(self, api_client):
        client, _ = api_client
        resp = client.get("/api/papers")
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("total", 0) == 0
        assert data.get("papers", []) == []


class TestStaticFrontend:
    def test_index_html_served(self, api_client):
        client, _ = api_client
        resp = client.get("/")
        assert resp.status_code == 200
        assert "Medical Affairs AI" in resp.text
        assert "Genpact" in resp.text

    def test_genpact_logo_asset(self, api_client):
        client, _ = api_client
        resp = client.get("/assets/genpact-logo-white.svg")
        assert resp.status_code == 200
        assert "svg" in resp.headers.get("content-type", "").lower() or resp.text.strip().startswith("<?xml")

    def test_pubmed_metrics_js_served(self, api_client):
        client, _ = api_client
        resp = client.get("/js/pubmed-metrics.js")
        assert resp.status_code == 200
        assert "buildPubMedMetrics" in resp.text
