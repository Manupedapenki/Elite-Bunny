"""GitHub webhook signature verification.

GitHub signs all webhook payloads with HMAC-SHA256 using the webhook secret.
This module verifies the signature before any payload processing.
"""
from __future__ import annotations

import hashlib
import hmac


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify the X-Hub-Signature-256 header against the webhook payload.

    Uses constant-time comparison to prevent timing attacks.

    Args:
        payload: Raw request body bytes.
        signature: Value of X-Hub-Signature-256 header (e.g., "sha256=abc123...").
        secret: GitHub webhook secret configured in the App.

    Returns:
        True if signature is valid, False otherwise.
    """
    if not secret:
        # No secret configured — skip verification (dev mode only)
        return True

    if not signature or not signature.startswith("sha256="):
        return False

    expected = "sha256=" + hmac.new(
        secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, signature)
