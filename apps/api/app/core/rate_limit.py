"""
PathForge API — Rate Limiter
===============================
Per-user rate limiting for expensive AI endpoints.

Uses SlowAPI with JWT-based user identification.
Storage backend is configurable: in-memory for development,
Redis for production (multi-instance correctness).

Sprint 29: Fixed audit C1 — storage_uri now reads from config.
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


# ── Limiter Instance ───────────────────────────────────────────
# Uses settings.ratelimit_storage_uri:
#   Development: memory:// (default)
#   Production:  redis://... (set via RATELIMIT_STORAGE_URI env var)

limiter = Limiter(
    key_func=_get_user_or_ip,
    default_limits=["200/minute"],
    storage_uri=settings.ratelimit_storage_uri,
)
