"""Post PR review comments and summary comments to GitHub."""
from __future__ import annotations

from typing import Any

import structlog

from .rest_client import GitHubRestClient

logger = structlog.get_logger()


class CommentPoster:
    """Posts review comments and summary comments to GitHub PRs."""

    def __init__(self, client: GitHubRestClient) -> None:
        self._client = client

    async def post_review(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        head_sha: str,
        comments: list[dict[str, Any]],
        body: str | None = None,
        event: str = "COMMENT",
    ) -> dict[str, Any]:
        """Post a batch of inline review comments on a PR.

        Uses the GitHub Pull Request Review API to post all comments
        in a single review, which is better UX than individual comments.

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            head_sha: The SHA of the commit being reviewed.
            comments: List of inline comment dicts with keys:
                - path: file path
                - line: line number in the diff
                - body: comment body (markdown)
                - side: "RIGHT" (default) or "LEFT"
            body: Optional review body text.
            event: Review event type (COMMENT, APPROVE, REQUEST_CHANGES).

        Returns:
            GitHub API response with review ID.
        """
        review_payload: dict[str, Any] = {
            "commit_id": head_sha,
            "event": event,
            "comments": comments,
        }
        if body:
            review_payload["body"] = body

        result = await self._client.post(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            json=review_payload,
        )

        logger.info(
            "github.review.posted",
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            comments_count=len(comments),
            review_id=result.get("id"),
        )
        return result

    async def post_summary_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> dict[str, Any]:
        """Post a summary comment on a PR (not inline).

        Uses the Issues API (which works for PR comments too).

        Args:
            owner: Repository owner.
            repo: Repository name.
            pr_number: Pull request number.
            body: Comment body (markdown).

        Returns:
            GitHub API response with comment ID.
        """
        result = await self._client.post(
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": body},
        )

        logger.info(
            "github.summary_comment.posted",
            owner=owner,
            repo=repo,
            pr_number=pr_number,
            comment_id=result.get("id"),
        )
        return result
