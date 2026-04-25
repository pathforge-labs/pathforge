"""
PathForge API — Middleware
=======================================
Request ID tracking, correlation ID propagation, request timing,
and security headers.

Sprint 30: Enhanced with correlation ID for distributed tracing,
request duration measurement, and OTel-compatible naming.

Features:
- Generates UUID4 per request (X-Request-ID)
- Accepts incoming X-Request-ID header (preserves client/gateway IDs)
- Propagates X-Correlation-ID for distributed tracing
- Measures request duration (duration_ms)
- Security headers (OWASP compliance) in production
"""

from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Context Variables ──────────────────────────────────────────
# Accessible from any async code in the same request lifecycle.
request_id_var: ContextVar[str] = ContextVar("request_id", default="")
correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="")


class RequestIDMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """
    Middleware that assigns a unique request ID and correlation ID.

    Request ID:
    - If X-Request-ID header exists, use it (gateway/client tracing)
    - Otherwise, generate a UUID4
    - Stores in contextvars for log binding
    - Returns X-Request-ID in response headers

    Correlation ID (distributed tracing):
    - If X-Correlation-ID header exists, propagate it
    - Otherwise, generate a new UUID4
    - OTel-compatible: used as trace_id in structured logs

    Duration:
    - Measures wall-clock time from request start to response
    - Returns X-Response-Time header (milliseconds)
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        start_time = time.perf_counter()

        # Request ID: use incoming or generate
        incoming_id = request.headers.get("x-request-id", "")
        rid = incoming_id if incoming_id else str(uuid.uuid4())

        # Correlation ID: use incoming or generate (distributed tracing)
        incoming_cid = request.headers.get("x-correlation-id", "")
        cid = incoming_cid if incoming_cid else str(uuid.uuid4())

        # Store in contextvars for log binding
        rid_token = request_id_var.set(rid)
        cid_token = correlation_id_var.set(cid)

        try:
            response = await call_next(request)

            # Calculate request duration
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            # Set response headers
            response.headers["X-Request-ID"] = rid
            response.headers["X-Correlation-ID"] = cid
            response.headers["X-Response-Time"] = f"{duration_ms}ms"

            # Log request completion with structured fields
            logger.info(
                "Request completed",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": duration_ms,
                },
            )

            return response
        finally:
            request_id_var.reset(rid_token)
            correlation_id_var.reset(cid_token)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """
    OWASP-compliant security headers middleware.

    Applies protective HTTP headers to all responses:
    - Prevents MIME-type sniffing (X-Content-Type-Options)
    - Prevents clickjacking (X-Frame-Options + CSP frame-ancestors)
    - Enforces HTTPS in production (Strict-Transport-Security)
    - Controls referrer information leakage
    - Restricts browser feature access (Permissions-Policy)
    - Locks down browser execution context (Content-Security-Policy)
    """

    # ── Content-Security-Policy (Sprint 39 audit F33) ─────────────
    #
    # PathForge's API returns JSON for every endpoint *except* the
    # interactive OpenAPI documentation. We therefore ship two
    # different CSP profiles:
    #
    # PROD: ultra-strict — there is no documented browser context that
    # legitimately renders an API response, so we forbid everything.
    # If an attacker manages to convince a browser to render a JSON
    # response inline (e.g. via a content-sniffing exploit) the CSP
    # forbids loading any scripts, styles, frames, or form posts.
    #
    # DEV: relaxed enough to let Swagger UI / ReDoc load from
    # ``cdn.jsdelivr.net``, since those endpoints exist *only* in
    # non-production environments (see ``main.create_app``).
    #
    # ``frame-ancestors 'none'`` mirrors ``X-Frame-Options: DENY`` for
    # browsers that prefer the modern directive; together they block
    # iframe embedding regardless of which check the browser honours.
    _CSP_PRODUCTION = (
        "default-src 'none'; "
        "frame-ancestors 'none'; "
        "form-action 'none'; "
        "base-uri 'none'; "
        "img-src 'self' data:; "
        "connect-src 'self'"
    )
    _CSP_DEVELOPMENT = (
        "default-src 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'; "
        "base-uri 'self'; "
        "img-src 'self' data: https://fastapi.tiangolo.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
        "connect-src 'self'"
    )

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # Always applied
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "0"  # Modern: rely on CSP, disable legacy filter
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"

        # CSP: stricter profile in production, looser in dev to keep
        # interactive OpenAPI docs functional. The header name is the
        # same in either branch — browsers don't see the env split.
        response.headers["Content-Security-Policy"] = (
            self._CSP_PRODUCTION
            if settings.is_production
            else self._CSP_DEVELOPMENT
        )

        # HSTS: only in production to avoid HTTPS enforcement in local dev
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )

        return response


# ── Bot Trap Paths ─────────────────────────────────────────────
# Common paths probed by vulnerability scanners and bots.
# Matching requests are short-circuited with 404 before route resolution.
BOT_TRAP_PREFIXES: tuple[str, ...] = (
    "/.env",
    "/.git",
    "/.aws",
    "/.docker",
    "/.vscode",
    "/.DS_Store",
    "/wp-admin",
    "/wp-login",
    "/wp-content",
    "/wp-includes",
    "/wordpress",
    "/actuator",
    "/graphql",
    "/graphiql",
    "/server-status",
    "/server-info",
    "/info.php",
    "/phpinfo",
    "/phpmyadmin",
    "/login.action",
    "/debug",
    "/console",
    "/v2/_catalog",
    "/config.json",
)

# Paths we explicitly handle (not trapped)
BOT_TRAP_EXCLUDES: frozenset[str] = frozenset({
    "/.well-known/security.txt",
})


class BotTrapMiddleware(BaseHTTPMiddleware):  # type: ignore[misc]
    """
    Short-circuit known vulnerability scanner probe paths.

    Returns 404 immediately without running route resolution for paths
    commonly probed by automated scanners. Only active in production
    to keep development open.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        path = request.url.path.lower()

        # Only trap in production
        if settings.is_production and path not in BOT_TRAP_EXCLUDES:
            for prefix in BOT_TRAP_PREFIXES:
                if path.startswith(prefix):
                    return Response(
                        content="Not Found",
                        status_code=404,
                        media_type="text/plain",
                    )

        return await call_next(request)


def get_request_id() -> str:
    """Get the current request ID from contextvars."""
    return request_id_var.get("")


def get_correlation_id() -> str:
    """Get the current correlation ID (trace_id) from contextvars."""
    return correlation_id_var.get("")
