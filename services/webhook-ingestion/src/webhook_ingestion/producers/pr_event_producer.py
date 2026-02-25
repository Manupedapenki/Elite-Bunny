"""PR event Kafka producer — publishes parsed PR events to pr.events topic.

The actual Kafka publishing is done directly in the PR handler using
the shared KafkaProducerWrapper. This module provides topic constants
and any PR-event-specific publishing utilities.
"""
from __future__ import annotations

# Kafka topic for PR events
PR_EVENTS_TOPIC = "pr.events"
