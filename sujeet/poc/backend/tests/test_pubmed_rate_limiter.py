"""Unit tests for PubMed E-utilities rate limiter."""

import time
from unittest.mock import MagicMock, patch

import pytest
import requests

from tools import pubmed_rate_limiter as rl


class TestConfigureRateLimit:
    def test_no_key_tier_accepts_up_to_three(self):
        assert rl.configure_rate_limit("no_api_key", 2.5, has_api_key=True) == 2.5

    def test_no_key_tier_rejects_above_three(self):
        with pytest.raises(ValueError, match="cannot exceed 3"):
            rl.configure_rate_limit("no_api_key", 5.0, has_api_key=True)

    def test_with_key_tier_requires_env_key(self):
        with pytest.raises(ValueError, match="requires PUBMED_API_KEY"):
            rl.configure_rate_limit("with_api_key", 5.0, has_api_key=False)

    def test_with_key_tier_accepts_up_to_ten(self):
        assert rl.configure_rate_limit("with_api_key", 10.0, has_api_key=True) == 10.0

    def test_rejects_zero_or_negative_rate(self):
        with pytest.raises(ValueError, match="greater than 0"):
            rl.configure_rate_limit("no_api_key", 0, has_api_key=False)


class TestPubMedRateLimiter:
    def test_configure_updates_interval(self):
        limiter = rl.PubMedRateLimiter(3)
        limiter.configure(2)
        assert limiter.max_requests_per_second == 2
        assert limiter.min_interval == pytest.approx(0.52, rel=0.01)

    def test_wait_enforces_minimum_spacing(self):
        limiter = rl.PubMedRateLimiter(10)
        limiter.configure(5)
        limiter.wait()
        start = time.monotonic()
        limiter.wait()
        elapsed = time.monotonic() - start
        assert elapsed >= limiter.min_interval * 0.9


class TestEutilsGet:
    @patch("tools.pubmed_rate_limiter.requests.get")
    def test_success_returns_response(self, mock_get):
        mock_resp = MagicMock(status_code=200)
        mock_get.return_value = mock_resp

        resp = rl.eutils_get("https://example.com/esearch", {"db": "pubmed"}, max_retries=1)
        assert resp.status_code == 200
        mock_get.assert_called_once()

    @patch("tools.pubmed_rate_limiter.time.sleep")
    @patch("tools.pubmed_rate_limiter.requests.get")
    def test_retries_on_429_then_succeeds(self, mock_get, mock_sleep):
        rate_limited = MagicMock(status_code=429, headers={"Retry-After": "1"})
        ok = MagicMock(status_code=200)
        mock_get.side_effect = [rate_limited, ok]

        resp = rl.eutils_get("https://example.com/esearch", {}, max_retries=3)
        assert resp.status_code == 200
        assert mock_get.call_count == 2
        mock_sleep.assert_called()

    @patch("tools.pubmed_rate_limiter.time.sleep")
    @patch("tools.pubmed_rate_limiter.requests.get")
    def test_raises_after_exhausted_429_retries(self, mock_get, mock_sleep):
        mock_get.return_value = MagicMock(status_code=429, headers={})

        with pytest.raises(rl.PubMedRateLimitError, match="rate limit exceeded"):
            rl.eutils_get("https://example.com/esearch", {}, max_retries=2)

    @patch("tools.pubmed_rate_limiter.requests.get")
    def test_retries_on_network_error(self, mock_get):
        mock_get.side_effect = [
            requests.ConnectionError("timeout"),
            MagicMock(status_code=200),
        ]

        resp = rl.eutils_get("https://example.com/esearch", {}, max_retries=2)
        assert resp.status_code == 200


class TestParseRetryAfter:
    def test_numeric_header(self):
        resp = MagicMock(headers={"Retry-After": "3"})
        assert rl._parse_retry_after(resp) == 3.0

    def test_invalid_header_defaults_to_two(self):
        resp = MagicMock(headers={"Retry-After": "soon"})
        assert rl._parse_retry_after(resp) == 2.0
