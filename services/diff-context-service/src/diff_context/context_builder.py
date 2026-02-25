"""Context builder — fetches surrounding code context for changed files."""
from __future__ import annotations

import mimetypes
from pathlib import PurePosixPath
from typing import Optional

import structlog

from common.models.diff_context import FileChange

from github_client.app_auth import GitHubAppAuth
from github_client.diff_fetcher import DiffFetcher
from github_client.file_fetcher import FileFetcher
from github_client.rest_client import GitHubRestClient

from .config import Settings
from .diff_parser import DiffParser

logger = structlog.get_logger()

# File extension to language mapping
LANGUAGE_MAP: dict[str, str] = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".jsx": "javascript", ".tsx": "typescript", ".java": "java",
    ".go": "go", ".rs": "rust", ".rb": "ruby", ".php": "php",
    ".c": "c", ".cpp": "cpp", ".cs": "csharp", ".swift": "swift",
    ".kt": "kotlin", ".scala": "scala", ".r": "r",
    ".sql": "sql", ".sh": "shell", ".bash": "shell",
    ".yaml": "yaml", ".yml": "yaml", ".json": "json",
    ".xml": "xml", ".html": "html", ".css": "css",
    ".md": "markdown", ".tf": "terraform", ".dockerfile": "dockerfile",
}


class ContextBuilder:
    """Fetches PR files from GitHub and enriches them with surrounding context.

    For each changed file, we:
    1. Parse the patch to find changed line ranges
    2. Fetch the full file content
    3. Extract N lines above and below each change
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._diff_parser = DiffParser()

    async def build_context(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        pr_number: int,
        head_sha: str,
    ) -> list[FileChange]:
        """Fetch PR files and enrich with surrounding context.

        Args:
            installation_id: GitHub App installation ID.
            owner: Repository owner.
            repo: Repository name.
            pr_number: PR number.
            head_sha: Head commit SHA.

        Returns:
            List of FileChange objects with surrounding context.
        """
        from .main import get_redis_client

        redis = get_redis_client()
        auth = GitHubAppAuth(
            app_id=self._settings.github_app_id,
            private_key_path=self._settings.github_private_key_path,
            redis_client=redis,
        )

        token = await auth.get_installation_token(installation_id)

        async with GitHubRestClient(token) as client:
            diff_fetcher = DiffFetcher(client)
            file_fetcher = FileFetcher(client, redis_client=redis)

            # Fetch PR files from GitHub
            pr_files = await diff_fetcher.fetch_pr_files(owner, repo, pr_number)

            file_changes: list[FileChange] = []
            for file_data in pr_files:
                file_path = file_data.get("filename", "")
                patch = file_data.get("patch", "")
                status = file_data.get("status", "modified")

                # Detect language from extension
                ext = PurePosixPath(file_path).suffix.lower()
                language = LANGUAGE_MAP.get(ext)

                # Fetch surrounding context
                surrounding = None
                if patch and status != "removed":
                    surrounding = await self._get_surrounding_context(
                        file_fetcher, owner, repo, file_path, head_sha, patch,
                    )

                file_changes.append(FileChange(
                    file_path=file_path,
                    status=status,
                    additions=file_data.get("additions", 0),
                    deletions=file_data.get("deletions", 0),
                    patch=patch,
                    language=language,
                    surrounding_context=surrounding,
                ))

        logger.info(
            "context.built",
            pr_number=pr_number,
            files_count=len(file_changes),
        )
        return file_changes

    async def _get_surrounding_context(
        self,
        file_fetcher: FileFetcher,
        owner: str,
        repo: str,
        file_path: str,
        ref: str,
        patch: str,
    ) -> Optional[str]:
        """Fetch surrounding context lines for a changed file.

        Extracts N lines above and below each changed hunk.
        """
        try:
            content = await file_fetcher.fetch_file_content(owner, repo, file_path, ref)
            if not content:
                return None

            lines = content.split("\n")
            changed_ranges = self._diff_parser.get_changed_line_ranges(patch)
            context_lines = self._settings.context_lines

            context_parts: list[str] = []
            for start, end in changed_ranges:
                ctx_start = max(0, start - context_lines - 1)  # 0-indexed
                ctx_end = min(len(lines), end + context_lines)
                context_chunk = lines[ctx_start:ctx_end]
                header = f"--- {file_path} (lines {ctx_start + 1}-{ctx_end}) ---"
                context_parts.append(header + "\n" + "\n".join(context_chunk))

            return "\n\n".join(context_parts) if context_parts else None
        except Exception:
            logger.warning("context.fetch_failed", file_path=file_path)
            return None
