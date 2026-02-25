"""GitHub webhook endpoint."""
from __future__ import annotations

import structlog
from fastapi import APIRouter, Header, Request, Response

from ..config import Settings
from ..handlers.pr_handler import handle_pr_event
from ..security.signature import verify_webhook_signature

logger = structlog.get_logger()
settings = Settings()

router = APIRouter(tags=["webhooks"])

# PR actions we care about
SUPPORTED_PR_ACTIONS = {"opened", "synchronize", "reopened"}


@router.post("/webhooks/github", status_code=202)
async def receive_github_webhook(
    request: Request,
    x_hub_signature_256: str = Header(None, alias="X-Hub-Signature-256"),
    x_github_delivery: str = Header(None, alias="X-GitHub-Delivery"),
    x_github_event: str = Header(None, alias="X-GitHub-Event"),
) -> Response:
    """Receive and process GitHub webhook events.

    Workflow:
    1. Verify webhook signature (HMAC-SHA256)
    2. Check if event type and action are supported
    3. Parse PR event and publish to Kafka
    4. Return 202 Accepted

    The response MUST be returned within 10 seconds (GitHub timeout).
    All heavy processing happens async via Kafka.
    """
    body = await request.body()

    # Step 1: Verify signature
    if not x_hub_signature_256:
        logger.warning("webhook.missing_signature", delivery_id=x_github_delivery)
        return Response(status_code=401, content="Missing signature")

    if not verify_webhook_signature(body, x_hub_signature_256, settings.github_webhook_secret):
        logger.warning("webhook.invalid_signature", delivery_id=x_github_delivery)
        return Response(status_code=401, content="Invalid signature")

    logger.info(
        "webhook.received",
        delivery_id=x_github_delivery,
        event_type=x_github_event,
    )

    # Step 2: Only process pull_request events
    if x_github_event != "pull_request":
        logger.info(
            "webhook.ignored",
            delivery_id=x_github_delivery,
            event_type=x_github_event,
            reason="not_pull_request",
        )
        return Response(status_code=200, content="Event type not handled")

    # Step 3: Parse payload and check action
    import json
    payload = json.loads(body)
    action = payload.get("action", "")

    if action not in SUPPORTED_PR_ACTIONS:
        logger.info(
            "webhook.ignored",
            delivery_id=x_github_delivery,
            action=action,
            reason="unsupported_action",
        )
        return Response(status_code=200, content="Action not handled")

    # Step 4: Handle the PR event (parse + publish to Kafka)
    try:
        await handle_pr_event(
            delivery_id=x_github_delivery or "unknown",
            payload=payload,
        )
    except Exception:
        logger.exception(
            "webhook.processing_error",
            delivery_id=x_github_delivery,
        )
        # Still return 202 — we've logged the event for retry
        return Response(status_code=500, content="Internal processing error")

    return Response(status_code=202, content="Accepted")
