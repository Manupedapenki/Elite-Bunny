"""Custom exception hierarchy for PR Intelligence Platform."""
from __future__ import annotations


class PRIntelligenceError(Exception):
    """Base exception for all PR Intelligence errors."""

    def __init__(self, message: str, delivery_id: str | None = None) -> None:
        self.delivery_id = delivery_id
        super().__init__(message)


# --- Webhook Errors ---

class WebhookError(PRIntelligenceError):
    """Base exception for webhook-related errors."""


class SignatureVerificationError(WebhookError):
    """GitHub webhook signature verification failed."""


class UnsupportedEventError(WebhookError):
    """Received an unsupported webhook event type."""


# --- GitHub API Errors ---

class GitHubAPIError(PRIntelligenceError):
    """Error communicating with GitHub API."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        delivery_id: str | None = None,
    ) -> None:
        self.status_code = status_code
        super().__init__(message, delivery_id)


class GitHubRateLimitError(GitHubAPIError):
    """GitHub API rate limit exceeded."""

    def __init__(
        self,
        message: str = "GitHub API rate limit exceeded",
        reset_at: int | None = None,
        delivery_id: str | None = None,
    ) -> None:
        self.reset_at = reset_at
        super().__init__(message, status_code=403, delivery_id=delivery_id)


class GitHubAuthError(GitHubAPIError):
    """GitHub authentication failed."""


# --- LLM Errors ---

class LLMError(PRIntelligenceError):
    """Base exception for LLM-related errors."""


class LLMResponseParseError(LLMError):
    """Failed to parse LLM response as JSON."""


class LLMRateLimitError(LLMError):
    """LLM API rate limit exceeded."""


class LLMTimeoutError(LLMError):
    """LLM API call timed out."""


# --- Analysis Errors ---

class AnalysisError(PRIntelligenceError):
    """Error during PR analysis."""


class DiffTooLargeError(AnalysisError):
    """PR diff exceeds maximum allowed size."""


class ChunkingError(AnalysisError):
    """Error during diff chunking."""


# --- Database Errors ---

class DatabaseError(PRIntelligenceError):
    """Database operation failed."""


class DuplicateReviewError(DatabaseError):
    """Attempted to create a duplicate review (idempotency check)."""
