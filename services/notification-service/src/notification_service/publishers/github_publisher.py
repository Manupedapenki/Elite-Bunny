"""GitHub publisher — posts review comments and summaries to GitHub PRs."""
from __future__ import annotations

from typing import Any

import structlog

from github_client.app_auth import GitHubAppAuth
from github_client.comment_poster import CommentPoster
from github_client.rest_client import GitHubRestClient

from ..config import Settings

logger = structlog.get_logger()


class GitHubPublisher:
    """Posts formatted comments to GitHub PRs via the GitHub API.

    Uses the GitHub Pull Request Review API for batched inline comments
    and the Issues API for summary comments.
    """

    def __init__(self, settings: Settings) -> None:
        self._auth = GitHubAppAuth(
            app_id=settings.github_app_id,
            private_key_path=settings.github_private_key_path,
        )

    async def post_review(
        self,
        installation_id: int,
        repository_full_name: str,
        pr_number: int,
        head_sha: str,
        comments: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Post inline review comments as a single PR review.

        Batches all inline comments into a single review for better UX.

        Args:
            installation_id: GitHub App installation ID.
            repository_full_name: "owner/repo" format.
            pr_number: PR number.
            head_sha: Commit SHA being reviewed.
            comments: List of inline comment dicts.

        Returns:
            GitHub API response.
        """
        token = await self._auth.get_installation_token(installation_id)
        owner, repo = repository_full_name.split("/", 1)

        async with GitHubRestClient(token) as client:
            poster = CommentPoster(client)
            result = await poster.post_review(
                owner=owner,
                repo=repo,
                pr_number=pr_number,
                head_sha=head_sha,
                comments=comments,
                event="COMMENT",
            )

        logger.info(
            "publisher.review_posted",
            repo=repository_full_name,
            pr_number=pr_number,
            comments=len(comments),
        )
        return result

    async def post_summary(
        self,
        installation_id: int,
        repository_full_name: str,
        pr_number: int,
        body: str,
    ) -> dict[str, Any]:
        """Post a summary comment on the PR.

        Args:
            installation_id: GitHub App installation ID.
            repository_full_name: "owner/repo" format.
            pr_number: PR number.
            body: Summary comment body (markdown).

        Returns:
            GitHub API response.
        """
        token = await self._auth.get_installation_token(installation_id)
        owner, repo = repository_full_name.split("/", 1)

        async with GitHubRestClient(token) as client:
            poster = CommentPoster(client)
            result = await poster.post_summary_comment(
                owner=owner,
                repo=repo,
                pr_number=pr_number,
                body=body,
            )

        logger.info(
            "publisher.summary_posted",
            repo=repository_full_name,
            pr_number=pr_number,
        )
        return result
