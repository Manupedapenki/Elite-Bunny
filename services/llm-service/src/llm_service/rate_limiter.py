"""Rate limiter for Claude API calls."""
from __future__ import annotations

import asyncio
import time

import structlog

logger = structlog.get_logger()


class LLMRateLimiter:
    """Simple token bucket rate limiter for LLM API calls.

    Limits requests per minute to stay within Claude API quotas.
    """

    def __init__(self, max_requests_per_minute: int = 50) -> None:
        self._max_rpm = max_requests_per_minute
        self._requests: list[float] = []

    async def wait_if_needed(self) -> None:
        """Wait if we've exceeded the rate limit."""
        now = time.time()

        # Remove requests older than 60 seconds
        self._requests = [t for t in self._requests if now - t < 60]

        if len(self._requests) >= self._max_rpm:
            # Wait until the oldest request expires
            wait_time = 60 - (now - self._requests[0]) + 0.1
            if wait_time > 0:
                logger.warning(
                    "llm.rate_limit.waiting",
                    requests_in_window=len(self._requests),
                    wait_seconds=wait_time,
                )
                await asyncio.sleep(wait_time)

        self._requests.append(time.time())

    def record_request(self) -> None:
        """Record that a request was made."""
        self._requests.append(time.time())
