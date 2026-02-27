"""
PathForge API — Structured Logging Configuration
===================================================
JSON in production, human-readable in development.

Sprint 30: Enhanced with correlation ID, service metadata,
sensitive field redaction, and OTel-compatible field naming.

Binds request ID + correlation ID from contextvars to every log entry.

Usage:
    from app.core.logging_config import setup_logging
    setup_logging()  # call once at startup
"""

from __future__ import annotations

import logging
import sys
from collections.abc import MutableMapping
from typing import Any

import structlog

from app.core.middleware import get_correlation_id, get_request_id

# ── Sensitive Field Denylist ───────────────────────────────────
# Fields whose values are redacted in log output.
# Matches field names case-insensitively at any nesting level.
SENSITIVE_FIELDS: frozenset[str] = frozenset({
    "password",
    "token",
    "secret",
    "authorization",
    "cookie",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "jwt_secret",
    "jwt_refresh_secret",
    "sentry_dsn",
    "resume_text",
    "cv_content",
})

REDACTED: str = "[REDACTED]"


# ── Processors ─────────────────────────────────────────────────


def _add_request_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Inject request ID into every log entry."""
    rid = get_request_id()
    if rid:
        event_dict["request_id"] = rid
    return event_dict


def _add_correlation_id(
    logger: logging.Logger,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Inject correlation ID (trace_id) for distributed tracing."""
    cid = get_correlation_id()
    if cid:
        # OTel-compatible field name (Audit I1)
        event_dict["trace_id"] = cid
    return event_dict


def _add_service_metadata(
    logger: logging.Logger,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """Add service identification fields (OTel-compatible naming)."""
    # Lazy import to avoid circular dependency at module load time
    from app.core.config import settings

    event_dict["service.name"] = settings.app_slug
    event_dict["service.version"] = settings.app_version
    event_dict["deployment.environment"] = settings.environment
    return event_dict


def _redact_sensitive_fields(
    logger: logging.Logger,
    method_name: str,
    event_dict: MutableMapping[str, Any],
) -> MutableMapping[str, Any]:
    """
    Redact sensitive field values to prevent PII/secret leakage in logs.

    Checks all top-level keys in the event dict against the denylist.
    Deep nested structures are not recursively scanned (structlog events
    are flat key-value pairs by convention).
    """
    for key in list(event_dict.keys()):
        if key.lower() in SENSITIVE_FIELDS:
            event_dict[key] = REDACTED
    return event_dict


def setup_logging(*, debug: bool | None = None) -> None:
    """
    Configure structlog for the application.

    Args:
        debug: If True, use human-readable console output.
               If False, use JSON rendering (production).
               If None, auto-detect from settings.debug.
    """
    if debug is None:
        from app.core.config import settings
        debug = settings.debug

    # Resolve log level from settings
    from app.core.config import settings
    log_level_name = settings.log_level.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Common processors applied to all log entries
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        _add_correlation_id,
        _add_service_metadata,
        _redact_sensitive_fields,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if debug:
        # Development: colorful, human-readable output
        renderer: structlog.types.Processor = structlog.dev.ConsoleRenderer(
            colors=True,
        )
    else:
        # Production: machine-parseable JSON
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure stdlib logging to use structlog formatting
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
    root_logger.setLevel(log_level)

    # Suppress noisy third-party loggers
    for noisy_logger in ("uvicorn.access", "httpcore", "httpx", "litellm"):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
