"""Unified diff format parser."""
from __future__ import annotations

import re
from dataclasses import dataclass

import structlog

logger = structlog.get_logger()


@dataclass
class DiffHunk:
    """A single hunk from a unified diff."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    content: str


class DiffParser:
    """Parses unified diff format to extract changed line ranges.

    Used to identify which lines changed so we can fetch
    surrounding context from the full file.
    """

    HUNK_HEADER_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")

    def parse_patch(self, patch: str) -> list[DiffHunk]:
        """Parse a unified diff patch into hunks.

        Args:
            patch: Unified diff patch string for a single file.

        Returns:
            List of DiffHunk objects with line ranges.
        """
        hunks: list[DiffHunk] = []
        if not patch:
            return hunks

        lines = patch.split("\n")
        current_hunk_lines: list[str] = []
        current_header: re.Match | None = None

        for line in lines:
            header_match = self.HUNK_HEADER_RE.match(line)
            if header_match:
                # Save previous hunk
                if current_header:
                    hunks.append(self._create_hunk(current_header, current_hunk_lines))
                current_header = header_match
                current_hunk_lines = [line]
            elif current_header:
                current_hunk_lines.append(line)

        # Save last hunk
        if current_header:
            hunks.append(self._create_hunk(current_header, current_hunk_lines))

        return hunks

    def _create_hunk(self, match: re.Match, lines: list[str]) -> DiffHunk:
        """Create a DiffHunk from regex match and content lines."""
        return DiffHunk(
            old_start=int(match.group(1)),
            old_count=int(match.group(2) or 1),
            new_start=int(match.group(3)),
            new_count=int(match.group(4) or 1),
            content="\n".join(lines),
        )

    def get_changed_line_ranges(self, patch: str) -> list[tuple[int, int]]:
        """Extract the line ranges that were changed (in the new file).

        Args:
            patch: Unified diff patch string.

        Returns:
            List of (start_line, end_line) tuples for changed ranges.
        """
        hunks = self.parse_patch(patch)
        ranges = []
        for hunk in hunks:
            start = hunk.new_start
            end = hunk.new_start + hunk.new_count - 1
            ranges.append((start, max(start, end)))
        return ranges
