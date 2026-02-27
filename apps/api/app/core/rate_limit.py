"""
PathForge API — Rate Limiter
===============================
Per-user rate limiting for expensive AI endpoints.

Uses SlowAPI with JWT-based user identification.
Storage backend is configurable: in-memory for development,
Redis for production (multi-instance correctness).

Sprint 29: Fixed audit C1 — storage_uri now reads from config.
Sprint 30: Redis failover (Audit C3), auth-specific rate limits.
"""

from __future__ import annotations

import logging

from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_user_or_ip(request: Request) -> str:
    """
    Extract rate-limit key from the request.

    Priority:
    1. Authenticated user ID (from JWT via request.state)
    2. Client IP address (fallback for unauthenticated requests)

    This ensures authenticated users are rate-limited per-user,
    not per-IP (important for shared networks/VPNs).
    """
    # FastAPI Depends populates request.state with user after auth
    user = getattr(request.state, "user", None)
    if user and hasattr(user, "id"):
        return f"user:{user.id}"
    return get_remote_address(request)


def _resolve_storage_uri() -> str:
    """
    Resolve rate limiter storage URI with Redis failover (Audit C3).

    Strategy:
    - If RATELIMIT_STORAGE_URI is explicitly set, use it
    - If Redis URL is available but storage URI is default, auto-configure Redis
    - On Redis connection failure, fall back to memory:// with CRITICAL log

    Matches Sprint 29 circuit breaker pattern for graceful degradation.
    """
    configured_uri = settings.ratelimit_storage_uri
    redis_url = settings.redis_url

    # If explicitly configured to non-default, use as-is
    if configured_uri != "memory://" and configured_uri:
        return configured_uri

    # Auto-configure Redis if available but storage URI is default
    if redis_url and configured_uri == "memory://":
        try:
            # Validate Redis connectivity before committing
            import redis as redis_lib

            parsed_url = redis_url
            if settings.redis_ssl and not parsed_url.startswith("rediss://"):
                parsed_url = parsed_url.replace("redis://", "rediss://", 1)

            client = redis_lib.Redis.from_url(
                parsed_url,
                socket_connect_timeout=2,
            )
            client.ping()
            client.close()

            logger.info(
                "Rate limiter using Redis storage",
                extra={"storage": "redis"},
            )
            return parsed_url

        except Exception:
            logger.critical(
                "Redis unavailable for rate limiting — falling back to in-memory storage. "
                "Rate limits will NOT be shared across instances.",
                extra={"storage": "memory", "degraded": True},
            )
            return "memory://"

    return configured_uri


# ── Storage State Tracking ─────────────────────────────────────
# Tracks whether rate limiting is operating in degraded mode
_resolved_uri = _resolve_storage_uri()
RATE_LIMIT_DEGRADED: bool = (
    _resolved_uri == "memory://" and bool(settings.redis_url)
)

# ── Limiter Instance ───────────────────────────────────────────
limiter = Limiter(
    key_func=_get_user_or_ip,
    default_limits=[settings.rate_limit_global_default],
    storage_uri=_resolved_uri,
)
