"""Frontend asset and UI contract tests (via FastAPI static serving + JS module)."""

import subprocess
from pathlib import Path

import pytest


FRONTEND_DIR = Path(__file__).resolve().parents[1]


class TestFrontendAssets:
    def test_index_contains_genpact_branding(self):
        html = (FRONTEND_DIR / "index.html").read_text(encoding="utf-8")
        assert "genpact-logo-white.svg" in html
        assert "Genpact" in html
        assert "pubmed-metrics.js" in html
        assert 'id="f-pubmed-tier"' in html
        assert 'id="pubmed-monitor-card"' in html

    def test_app_js_uses_pubmed_metrics_module(self):
        js = (FRONTEND_DIR / "app.js").read_text(encoding="utf-8")
        assert "PubMedMetrics" in js or "buildPubMedMetrics" in js

    def test_style_has_genpact_theme_variables(self):
        css = (FRONTEND_DIR / "style.css").read_text(encoding="utf-8")
        assert "--gp-dark-blue" in css
        assert "--gp-cyan" in css
        assert "--gp-red" in css

    def test_logo_assets_exist(self):
        assert (FRONTEND_DIR / "assets" / "genpact-logo-white.svg").exists()
        assert (FRONTEND_DIR / "assets" / "genpact-logo-color.svg").exists()


class TestPubMedMetricsJs:
    def test_node_unit_tests_pass(self):
        test_file = FRONTEND_DIR / "tests" / "metrics.test.js"
        result = subprocess.run(
            ["node", "--test", str(test_file)],
            capture_output=True,
            text=True,
            cwd=str(FRONTEND_DIR),
        )
        assert result.returncode == 0, result.stdout + result.stderr
