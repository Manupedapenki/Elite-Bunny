#!/usr/bin/env python3
"""Simulate a GitHub webhook POST to the local webhook-ingestion service.

Usage:
    python scripts/test_webhook_locally.py [--url http://localhost:8001]
    python scripts/test_webhook_locally.py --secret your_webhook_secret

This script reads the sample webhook payload from tests/fixtures/,
generates a valid HMAC-SHA256 signature, and sends it to the local service.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
from pathlib import Path

import httpx


def generate_signature(payload: bytes, secret: str) -> str:
    """Generate X-Hub-Signature-256 header value."""
    signature = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Test webhook locally")
    parser.add_argument("--url", default="http://localhost:8001/webhooks/github")
    parser.add_argument("--secret", default="test-secret")
    args = parser.parse_args()

    # Load sample payload
    fixture_path = Path(__file__).parent.parent / "tests" / "fixtures" / "sample_pr_webhook.json"
    if not fixture_path.exists():
        print(f"Error: Fixture not found at {fixture_path}")
        sys.exit(1)

    payload = fixture_path.read_bytes()
    signature = generate_signature(payload, args.secret)

    print(f"Sending webhook to {args.url}")
    print(f"Payload size: {len(payload)} bytes")
    print(f"Signature: {signature[:30]}...")

    try:
        response = httpx.post(
            args.url,
            content=payload,
            headers={
                "Content-Type": "application/json",
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "test-delivery-001",
                "X-Hub-Signature-256": signature,
            },
        )
        print(f"\nResponse status: {response.status_code}")
        print(f"Response body: {response.text}")

        if response.status_code == 202:
            print("\n✅ Webhook accepted! Check Kafka for the message.")
        elif response.status_code == 401:
            print("\n❌ Signature verification failed. Check your --secret matches GITHUB_WEBHOOK_SECRET.")
        else:
            print(f"\n⚠️ Unexpected status code: {response.status_code}")

    except httpx.ConnectError:
        print(f"\n❌ Could not connect to {args.url}")
        print("Make sure the webhook-ingestion service is running:")
        print("  docker-compose up webhook-ingestion")
        sys.exit(1)


if __name__ == "__main__":
    main()
