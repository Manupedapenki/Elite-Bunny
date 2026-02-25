"""Fetch full file content from GitHub API."""
from __future__ import annotations

import base64
from typing import Optional

import structlog

from .rest_client import GitHubRestClient

logger = structlog.get_logger()


class FileFetcher:
    """Fetches file content from GitHub at a specific commit SHA."""

    def __init__(self, client: GitHubRestClient, redis_client: Optional[object] = None) -> None:
        self._client = client
        self._redis = redis_client

    async def fetch_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        ref: str,
    ) -> Optional[str]:
        """Fetch file content at a specific ref (commit SHA or branch).

        Results are cached in Redis for 1 hour.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: File path within the repository.
            ref: Git ref (commit SHA or branch name).

        Returns:
            File content as string, or None if not found.
        """
        cache_key = f"file:{owner}/{repo}:{ref}:{path}"

        # Check Redis cache
        if self._redis:
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    logger.debug("github.file.cache_hit", path=path, ref=ref[:8])
                    return cached.decode("utf-8") if isinstance(cached, bytes) else cached
            except Exception:
                logger.warning("github.file.redis_error", path=path)

        try:
            data = await self._client.get(
                f"/repos/{owner}/{repo}/contents/{path}",
                params={"ref": ref},
            )
        except Exception:
            logger.warning("github.file.not_found", path=path, ref=ref[:8])
            return None

        if data.get("encoding") == "base64" and data.get("content"):
            content = base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        else:
            logger.warning("github.file.unsupported_encoding", path=path, encoding=data.get("encoding"))
            return None

        # Cache in Redis (TTL 1 hour)
        if self._redis:
            try:
                await self._redis.setex(cache_key, 3600, content)
            except Exception:
                logger.warning("github.file.redis_cache_error", path=path)

        logger.debug("github.file.fetched", path=path, ref=ref[:8], size=len(content))
        return content
