"""Pydantic model for PR webhook event payload."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class PREventPayload(BaseModel):
    """Represents a parsed PR webhook event, published to Kafka pr.events topic."""

    delivery_id: str = Field(..., description="X-GitHub-Delivery header")
    action: str = Field(..., description="opened | synchronize | reopened")
    installation_id: int
    repository_id: int
    repository_full_name: str  # e.g., "owner/repo"
    repository_owner: str
    repository_name: str
    repository_default_branch: str
    pr_number: int
    pr_title: str
    pr_description: Optional[str] = None
    pr_author: str
    head_sha: str
    base_branch: str
    head_branch: str
    pr_url: str
    diff_url: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
