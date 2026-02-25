"""Fetch PR diff and file list from GitHub API."""
from __future__ import annotations

from typing import Any

import structlog

from .rest_client import GitHubRestClient

logger = structlog.get_logger()


class DiffFetcher:
    """Fetches PR file changes and diffs from GitHub API."""

    def __init__(self, client: GitHubRestClient) -> None:
        self._client = client

    async def fetch_pr_files(
        self,
        owner: str,
        repo: str,
        pr_number: int,
    ) -> list[dict[str, Any]]:
        """Fetch the list of files changed in a PR.

        Uses pagination to handle PRs with many changed files.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            List of file change dicts from GitHub API.
        """
        all_files: list[dict[str, Any]] = []
        page = 1
        per_page = 100

        while True:
            files = await self._client.get(
                f"/repos/{owner}/{repo}/pulls/{pr_number}/files",
                params={"per_page": per_page, "page": page},
            )
            if not files:
                break
            all_files.extend(files)
            if len(files) < per_page:
                break
            page += 1

        logger.info(
            "github.diff.fetched",
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            files_count=len(all_files),
        )
        return all_files

    async def fetch_raw_diff(self, owner: str, repo: str, pr_number: int) -> str:
        """Fetch the raw unified diff for a PR.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.

        Returns:
            Raw unified diff as string.
        """
        diff = await self._client.get_raw(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        logger.info(
            "github.raw_diff.fetched",
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            diff_size=len(diff),
        )
        return diff
