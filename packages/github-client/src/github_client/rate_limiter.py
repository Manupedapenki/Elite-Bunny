"""GitHub API rate limiter."""
from __future__ import annotations

import asyncio
import time
from typing import Any, Mapping

import structlog

logger = structlog.get_logger()


class GitHubRateLimiter:
    """Token bucket rate limiter for GitHub API.

    Tracks remaining requests from GitHub response headers and
    sleeps when the limit is about to be exceeded.
    """

    def __init__(self, min_remaining: int = 10) -> None:
        self._min_remaining = min_remaining
        self._remaining: int = 5000  # GitHub default
        self._reset_at: float = 0.0
        self._limit: int = 5000

    def update_from_headers(self, headers: Mapping[str, Any]) -> None:
        """Update rate limit state from GitHub response headers."""
        if "x-ratelimit-remaining" in headers:
            self._remaining = int(headers["x-ratelimit-remaining"])
        if "x-ratelimit-reset" in headers:
            self._reset_at = float(headers["x-ratelimit-reset"])
        if "x-ratelimit-limit" in headers:
            self._limit = int(headers["x-ratelimit-limit"])

    async def wait_if_needed(self) -> None:
        """Sleep if we're close to the rate limit."""
        if self._remaining <= self._min_remaining and self._reset_at > 0:
            wait_time = max(0, self._reset_at - time.time() + 1)
            if wait_time > 0:
                logger.warning(
                    "github.rate_limit.waiting",
                    remaining=self._remaining,
                    wait_seconds=wait_time,
                )
                await asyncio.sleep(wait_time)

    async def handle_rate_limit(self, headers: Mapping[str, Any]) -> None:
        """Handle a 403 rate limit response by sleeping until reset."""
        self.update_from_headers(headers)
        wait_time = max(0, self._reset_at - time.time() + 1)
        logger.warning(
            "github.rate_limit.exceeded",
            reset_in_seconds=wait_time,
            limit=self._limit,
        )
        await asyncio.sleep(min(wait_time, 60))  # Cap at 60s wait
