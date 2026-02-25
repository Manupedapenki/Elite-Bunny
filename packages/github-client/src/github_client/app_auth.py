"""GitHub App authentication — JWT generation and installation token management."""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import httpx
import jwt
import structlog

logger = structlog.get_logger()

GITHUB_API_BASE = "https://api.github.com"


class GitHubAppAuth:
    """Handles GitHub App authentication via JWT and installation tokens.

    GitHub Apps authenticate in two steps:
    1. Generate a JWT signed with the App's private key (valid 10 min)
    2. Exchange the JWT for an installation token (valid 1 hour)

    Installation tokens are cached in Redis to avoid unnecessary API calls.
    """

    def __init__(
        self,
        app_id: str,
        private_key_path: str,
        redis_client: Optional[object] = None,
    ) -> None:
        self._app_id = app_id
        self._private_key = Path(private_key_path).read_text()
        self._redis = redis_client
        self._token_cache: dict[int, tuple[str, float]] = {}  # installation_id -> (token, expires_at)

    def _generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication.

        The JWT is signed with the App's private key using RS256.
        Valid for 10 minutes (GitHub's maximum).
        """
        now = int(time.time())
        payload = {
            "iat": now - 60,  # issued at (60s in the past for clock skew)
            "exp": now + (10 * 60),  # expires in 10 minutes
            "iss": self._app_id,
        }
        token = jwt.encode(payload, self._private_key, algorithm="RS256")
        logger.debug("github.jwt.generated", app_id=self._app_id)
        return token

    async def get_installation_token(self, installation_id: int) -> str:
        """Get an installation token, using cache if available.

        Args:
            installation_id: GitHub App installation ID.

        Returns:
            A valid installation access token.
        """
        # Check in-memory cache first
        if installation_id in self._token_cache:
            token, expires_at = self._token_cache[installation_id]
            if time.time() < expires_at - 60:  # 60s buffer before expiry
                return token

        # Check Redis cache
        if self._redis:
            cache_key = f"github:installation_token:{installation_id}"
            try:
                cached = await self._redis.get(cache_key)
                if cached:
                    logger.debug("github.token.cache_hit", installation_id=installation_id)
                    return cached.decode("utf-8") if isinstance(cached, bytes) else cached
            except Exception:
                logger.warning("github.token.redis_error", installation_id=installation_id)

        # Generate new token
        app_jwt = self._generate_jwt()
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {app_jwt}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )
            response.raise_for_status()

        data = response.json()
        token = data["token"]
        expires_at_str = data.get("expires_at", "")

        # Cache in memory (1 hour - 60s buffer)
        self._token_cache[installation_id] = (token, time.time() + 3540)

        # Cache in Redis
        if self._redis:
            try:
                cache_key = f"github:installation_token:{installation_id}"
                await self._redis.setex(cache_key, 3540, token)
            except Exception:
                logger.warning("github.token.redis_cache_error", installation_id=installation_id)

        logger.info(
            "github.token.created",
            installation_id=installation_id,
            expires_at=expires_at_str,
        )
        return token
