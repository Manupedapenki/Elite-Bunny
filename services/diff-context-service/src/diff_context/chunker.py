"""Diff chunker — splits large PRs into manageable chunks for LLM analysis."""
from __future__ import annotations

import structlog

from common.models.diff_context import FileChange

from .config import Settings

logger = structlog.get_logger()


class DiffChunker:
    """Splits large PRs into multiple chunks for processing.

    If a PR has too many files or the total diff is too large,
    we split into chunks that can each be analyzed independently.
    """

    def __init__(self, settings: Settings) -> None:
        self._max_files = settings.max_files_per_analysis
        self._max_bytes = settings.max_diff_size_bytes

    def chunk_files(self, files: list[FileChange]) -> list[list[FileChange]]:
        """Split files into chunks based on count and size limits.

        Args:
            files: List of all changed files in the PR.

        Returns:
            List of file chunks, each within the configured limits.
        """
        if not files:
            return [[]]

        # If within limits, return as single chunk
        total_size = sum(len(f.patch.encode("utf-8")) for f in files)
        if len(files) <= self._max_files and total_size <= self._max_bytes:
            return [files]

        # Split into chunks
        chunks: list[list[FileChange]] = []
        current_chunk: list[FileChange] = []
        current_size = 0

        for file in files:
            file_size = len(file.patch.encode("utf-8"))

            # Start new chunk if adding this file would exceed limits
            if current_chunk and (
                len(current_chunk) >= self._max_files
                or current_size + file_size > self._max_bytes
            ):
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0

            current_chunk.append(file)
            current_size += file_size

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)

        logger.info(
            "chunker.split",
            total_files=len(files),
            total_size=total_size,
            chunks=len(chunks),
        )
        return chunks
