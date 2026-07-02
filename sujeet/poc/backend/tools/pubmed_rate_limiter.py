"""
PubMed E-utilities rate limiter
================================
NCBI allows 3 requests/second without an API key and 10 requests/second
with an API key. This module enforces user-selected limits and retries
429 responses.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

import requests

NCBI_MAX_RPS_NO_KEY = 3
NCBI_MAX_RPS_WITH_KEY = 10
NCBI_DISCLOSURE = (
    "E-utils users are allowed 3 requests/second without an API key. "
    "Create an API key to increase your e-utils limit to 10 requests/second."
)


class PubMedRateLimitError(Exception):
    """Raised when PubMed rate limits cannot be satisfied after retries."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class PubMedRateLimiter:
    """Thread-safe limiter that spaces E-utilities calls to stay under NCBI caps."""

    def __init__(self, max_requests_per_second: float = NCBI_MAX_RPS_NO_KEY):
        self._lock = threading.Lock()
        self._last_request_at = 0.0
        self.configure(max_requests_per_second)

    def configure(self, max_requests_per_second: float) -> None:
        if max_requests_per_second <= 0:
            raise ValueError("requests_per_second must be greater than 0")
        self.max_requests_per_second = max_requests_per_second
        # Small safety margin so we stay strictly under the NCBI cap.
        self.min_interval = (1.0 / max_requests_per_second) + 0.02

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            elapsed = now - self._last_request_at
            if elapsed < self.min_interval:
                time.sleep(self.min_interval - elapsed)
            self._last_request_at = time.monotonic()


# Shared limiter instance used by pubmed_tools.
_rate_limiter = PubMedRateLimiter(NCBI_MAX_RPS_NO_KEY)


def get_rate_limiter() -> PubMedRateLimiter:
    return _rate_limiter


def configure_rate_limit(
    tier: str,
    requests_per_second: float,
    has_api_key: bool,
) -> float:
    """
    Validate and apply a user-selected PubMed rate limit.
    Returns the effective requests-per-second value.
    """
    cap = NCBI_MAX_RPS_WITH_KEY if tier == "with_api_key" else NCBI_MAX_RPS_NO_KEY

    if tier == "with_api_key" and not has_api_key:
        raise ValueError(
            "PubMed tier 'with_api_key' requires PUBMED_API_KEY in backend/.env"
        )

    if requests_per_second <= 0:
        raise ValueError("requests_per_second must be greater than 0")

    if requests_per_second > cap:
        raise ValueError(
            f"requests_per_second cannot exceed {cap} for tier '{tier}' "
            f"(NCBI E-utilities limit)"
        )

    _rate_limiter.configure(requests_per_second)
    return requests_per_second


def eutils_get(
    url: str,
    params: dict,
    *,
    timeout: int = 30,
    max_retries: int = 4,
) -> requests.Response:
    """
    Perform a rate-limited GET to NCBI E-utilities with retry on 429/503.
    """
    last_error: Optional[Exception] = None

    for attempt in range(max_retries):
        _rate_limiter.wait()
        try:
            resp = requests.get(url, params=params, timeout=timeout)
        except requests.RequestException as exc:
            last_error = exc
            if attempt + 1 >= max_retries:
                raise PubMedRateLimitError(
                    f"PubMed request failed after {max_retries} attempts: {exc}"
                ) from exc
            time.sleep(min(2 ** attempt, 8))
            continue

        if resp.status_code == 429:
            retry_after = _parse_retry_after(resp)
            last_error = PubMedRateLimitError(
                f"PubMed rate limit exceeded (HTTP 429). "
                f"Retrying in {retry_after:.1f}s.",
                status_code=429,
            )
            time.sleep(retry_after)
            continue

        if resp.status_code in (502, 503, 504):
            last_error = PubMedRateLimitError(
                f"PubMed temporarily unavailable (HTTP {resp.status_code}).",
                status_code=resp.status_code,
            )
            time.sleep(min(2 ** attempt, 8))
            continue

        return resp

    if isinstance(last_error, PubMedRateLimitError):
        raise PubMedRateLimitError(
            "PubMed rate limit exceeded. Lower requests/second or wait before retrying.",
            status_code=429,
        ) from last_error

    raise PubMedRateLimitError(
        f"PubMed request failed after {max_retries} attempts: {last_error}"
    )


def _parse_retry_after(resp: requests.Response) -> float:
    raw = resp.headers.get("Retry-After", "2")
    try:
        return max(float(raw), 1.0)
    except ValueError:
        return 2.0
