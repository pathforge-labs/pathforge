"""
PathForge API — Sentry Error Tracking
========================================
Sentry SDK initialization with production-grade configuration.

Sprint 30 WS-1: Implements Audit findings:
- H1: EventScrubber with DEFAULT_DENYLIST for recursive PII scrubbing
- H4: Sampling ramp strategy (1.0 → 0.1 after baseline week)
- M2: Custom LLM error fingerprinting for effective issue grouping
- C2: Flush on graceful shutdown (handled in main.py lifespan)

Usage:
    from app.core.sentry import init_sentry
    init_sentry()  # call once at startup
"""

from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


def _before_send(
    event: dict[str, Any],
    hint: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Event filter applied before sending to Sentry.

    Performs:
    - Custom LLM error fingerprinting (Audit M2)
    - Adds service context metadata
    """
    # ── LLM Error Fingerprinting (Audit M2) ────────────────────
    # Group LLM errors by [provider, error_type] instead of stack trace
    exception_info = hint.get("exc_info")
    if exception_info:
        exc_type = exception_info[0]
        exc_value = exception_info[1]

        if exc_type and _is_llm_error(exc_type.__name__, str(exc_value)):
            provider = _extract_llm_provider(str(exc_value))
            error_category = _categorize_llm_error(str(exc_value))
            event["fingerprint"] = ["llm-error", provider, error_category]
            event.setdefault("tags", {}).update({
                "llm.provider": provider,
                "llm.error_category": error_category,
            })

    # ── Service Context ────────────────────────────────────────
    event.setdefault("tags", {}).update({
        "service": settings.app_slug,
        "deployment.environment": settings.environment,
    })

    return event


def _is_llm_error(exc_name: str, message: str) -> bool:
    """Check if an exception is LLM-related."""
    llm_indicators = (
        "litellm",
        "openai",
        "gemini",
        "anthropic",
        "api_error",
        "quota",
        "rate_limit",
        "model_not_found",
        "context_length",
        "content_filter",
    )
    combined = f"{exc_name} {message}".lower()
    return any(indicator in combined for indicator in llm_indicators)


def _extract_llm_provider(message: str) -> str:
    """Extract LLM provider name from error message."""
    message_lower = message.lower()
    providers = {
        "gemini": "google",
        "google": "google",
        "openai": "openai",
        "gpt": "openai",
        "anthropic": "anthropic",
        "claude": "anthropic",
        "litellm": "litellm-proxy",
    }
    for keyword, provider in providers.items():
        if keyword in message_lower:
            return provider
    return "unknown"


def _categorize_llm_error(message: str) -> str:
    """Categorize LLM error for fingerprinting."""
    message_lower = message.lower()
    categories = {
        "quota": "quota_exceeded",
        "rate_limit": "rate_limited",
        "rate limit": "rate_limited",
        "429": "rate_limited",
        "context_length": "context_overflow",
        "context length": "context_overflow",
        "content_filter": "content_filtered",
        "safety": "content_filtered",
        "timeout": "timeout",
        "connection": "connection_error",
        "authentication": "auth_error",
        "401": "auth_error",
        "403": "auth_error",
        "model_not_found": "model_not_found",
    }
    for keyword, category in categories.items():
        if keyword in message_lower:
            return category
    return "unknown_llm_error"


def init_sentry() -> None:
    """
    Initialize Sentry SDK if DSN is configured.

    Does nothing when SENTRY_DSN is empty — zero overhead in development.
    """
    if not settings.sentry_dsn:
        logger.info("Sentry: disabled (no DSN configured)")
        return

    try:
        import sentry_sdk
        from sentry_sdk.scrubber import DEFAULT_DENYLIST, EventScrubber

        # Extended denylist with PathForge-specific fields (Audit H1)
        extended_denylist = [
            *DEFAULT_DENYLIST,
            "resume_text",
            "cv_content",
            "cover_letter",
            "job_description",
        ]

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            # Environment and release
            environment=settings.sentry_environment or settings.environment,
            release=settings.sentry_release or settings.app_version,
            # Performance monitoring (Audit H4: start at 1.0, ramp down)
            traces_sample_rate=settings.sentry_traces_sample_rate,
            # PII scrubbing (Audit H1: recursive deep scrubbing)
            event_scrubber=EventScrubber(
                denylist=extended_denylist,
                recursive=True,
            ),
            send_default_pii=False,
            # Custom event processing
            before_send=_before_send,
            # Integration configuration
            integrations=[],  # FastAPI auto-detected
            # Attach server name for multi-instance tracing
            server_name=settings.app_slug,
        )

        logger.info(
            "Sentry initialized",
            extra={
                "environment": settings.sentry_environment or settings.environment,
                "traces_sample_rate": settings.sentry_traces_sample_rate,
            },
        )

    except ImportError:
        logger.warning(
            "Sentry SDK not installed — error tracking disabled. "
            "Install with: pip install sentry-sdk[fastapi]"
        )
    except Exception:
        logger.exception("Failed to initialize Sentry")
