"""
PathForge API — Global Exception Handlers
============================================
Consistent error responses with request ID tracing.

Registered on the FastAPI app in main.py.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.llm import LLMError
from app.core.middleware import get_request_id

logger = logging.getLogger(__name__)


# ── Error Response Schema ──────────────────────────────────────

def _error_response(
    status_code: int,
    detail: str,
    error_type: str = "server_error",
) -> JSONResponse:
    """Create a consistent error JSON response with request ID."""
    body: dict[str, Any] = {
        "error": error_type,
        "detail": detail,
        "request_id": get_request_id(),
    }
    return JSONResponse(status_code=status_code, content=body)


# ── Exception Handlers ─────────────────────────────────────────

async def llm_error_handler(_request: Request, exc: LLMError) -> JSONResponse:
    """
    Handle LLMError (all LLM tiers exhausted).

    Returns 503 Service Unavailable — the AI service is temporarily
    degraded, client should retry with backoff.
    """
    logger.error(
        "LLM service unavailable [request_id=%s]: %s",
        get_request_id(),
        str(exc)[:300],
    )

    # Sprint 30 WS-1: Capture to Sentry with LLM context
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    except ImportError:
        pass

    return _error_response(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="AI service is temporarily unavailable. Please try again shortly.",
        error_type="ai_service_unavailable",
    )


async def value_error_handler(_request: Request, exc: ValueError) -> JSONResponse:
    """
    Handle ValueError from validation or business logic.

    Returns 422 Unprocessable Entity with the error detail.
    """
    logger.warning(
        "Validation error [request_id=%s]: %s",
        get_request_id(),
        str(exc)[:200],
    )
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(exc),
        error_type="validation_error",
    )


async def generic_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Catch-all handler for unexpected exceptions.

    Logs the full traceback server-side, returns a safe message to the client.
    Never leaks internal details, stack traces, or sensitive information.
    """
    logger.exception(
        "Unhandled exception [request_id=%s]: %s",
        get_request_id(),
        str(exc)[:200],
    )

    # Sprint 30 WS-1: Capture unhandled exceptions to Sentry
    try:
        import sentry_sdk
        sentry_sdk.capture_exception(exc)
    except ImportError:
        pass

    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="An unexpected error occurred. Please contact support with your request ID.",
        error_type="internal_error",
    )


# ── Registration ───────────────────────────────────────────────

def register_error_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app."""
    app.add_exception_handler(LLMError, llm_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(ValueError, value_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, generic_error_handler)
