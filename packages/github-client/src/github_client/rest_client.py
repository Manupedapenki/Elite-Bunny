"""GitHub REST API client wrapper."""
from __future__ import annotations

from typing import Any, Optional

import httpx
import structlog

from .rate_limiter import GitHubRateLimiter

logger = structlog.get_logger()

GITHUB_API_BASE = "https://api.github.com"


class GitHubRestClient:
    """Async HTTP client for GitHub REST API with rate limiting.

    Wraps httpx.AsyncClient with authentication headers,
    rate limit handling, and structured logging.
    """

    def __init__(self, token: str, rate_limiter: Optional[GitHubRateLimiter] = None) -> None:
        self._token = token
        self._rate_limiter = rate_limiter or GitHubRateLimiter()
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> GitHubRestClient:
        """Open the HTTP client."""
        self._client = httpx.AsyncClient(
            base_url=GITHUB_API_BASE,
            headers={
                "Authorization": f"token {self._token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()

    async def get(self, path: str, params: Optional[dict[str, Any]] = None) -> Any:
        """Make a GET request to the GitHub API.

        Args:
            path: API path (e.g., /repos/owner/repo/pulls/1/files).
            params: Optional query parameters.

        Returns:
            Parsed JSON response.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use as async context manager.")

        await self._rate_limiter.wait_if_needed()

        response = await self._client.get(path, params=params)
        self._rate_limiter.update_from_headers(response.headers)

        if response.status_code == 403 and "rate limit" in response.text.lower():
            await self._rate_limiter.handle_rate_limit(response.headers)
            response = await self._client.get(path, params=params)

        response.raise_for_status()
        logger.debug("github.api.get", path=path, status=response.status_code)
        return response.json()

    async def post(self, path: str, json: Optional[dict[str, Any]] = None) -> Any:
        """Make a POST request to the GitHub API.

        Args:
            path: API path.
            json: Request body as dict.

        Returns:
            Parsed JSON response.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use as async context manager.")

        await self._rate_limiter.wait_if_needed()

        response = await self._client.post(path, json=json)
        self._rate_limiter.update_from_headers(response.headers)
        response.raise_for_status()

        logger.debug("github.api.post", path=path, status=response.status_code)
        return response.json()

    async def get_raw(self, path: str) -> str:
        """Make a GET request returning raw text (for diffs).

        Args:
            path: API path.

        Returns:
            Raw response text.
        """
        if not self._client:
            raise RuntimeError("Client not initialized. Use as async context manager.")

        await self._rate_limiter.wait_if_needed()

        response = await self._client.get(
            path,
            headers={"Accept": "application/vnd.github.v3.diff"},
        )
        self._rate_limiter.update_from_headers(response.headers)
        response.raise_for_status()
        return response.text
