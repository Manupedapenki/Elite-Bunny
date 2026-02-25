"""Structured JSON logging setup using structlog."""
from __future__ import annotations

import logging
import sys

import structlog


def setup_logging(service_name: str, log_level: str = "INFO") -> None:
    """Configure structured JSON logging for a service.

    Sets up structlog with JSON rendering, timestamp injection,
    and log level filtering. All log lines include service_name.

    Args:
        service_name: Name of the service (included in every log line).
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
    """
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.StackInfoRenderer(),
            structlog.dev.set_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper(), logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Bind service name to all loggers via contextvars
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(service=service_name)
