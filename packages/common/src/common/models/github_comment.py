"""Pydantic models for GitHub PR comments."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class InlineComment(BaseModel):
    """A single inline review comment to post on a PR."""

    file_path: str
    line_number: int
    body: str
    side: str = "RIGHT"  # LEFT or RIGHT side of diff


class ReviewRequest(BaseModel):
    """A batch of inline comments to post as a PR review."""

    repository_full_name: str
    pr_number: int
    head_sha: str
    event: str = "COMMENT"  # COMMENT, APPROVE, or REQUEST_CHANGES
    body: Optional[str] = None  # Review body text
    comments: list[InlineComment]


class SummaryComment(BaseModel):
    """A summary comment to post on a PR (not inline)."""

    repository_full_name: str
    pr_number: int
    body: str


class PostedComment(BaseModel):
    """Record of a comment that was posted to GitHub."""

    review_id: str
    finding_id: Optional[str] = None
    github_comment_id: int
    comment_type: str  # 'inline_review' or 'summary'
    body: str
    posted_at: datetime
