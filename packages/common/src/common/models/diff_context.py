"""Pydantic models for enriched diff context."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class FileChange(BaseModel):
    """A single file changed in the PR."""

    file_path: str
    status: str  # added, modified, removed, renamed
    additions: int
    deletions: int
    patch: str  # unified diff for this file
    language: Optional[str] = None
    surrounding_context: Optional[str] = None  # 20 lines above/below


class DiffContext(BaseModel):
    """Enriched diff data ready for LLM analysis. Published to analysis.requests."""

    delivery_id: str
    installation_id: int
    repository_full_name: str
    pr_number: int
    pr_title: str
    pr_description: Optional[str] = None
    pr_author: str
    head_sha: str
    base_branch: str
    head_branch: str
    files: list[FileChange]
    total_additions: int
    total_deletions: int
    total_files_changed: int
    is_chunked: bool = False
    chunk_index: int = 0
    total_chunks: int = 1
