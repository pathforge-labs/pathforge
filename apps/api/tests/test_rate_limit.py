"""
PathForge — Rate Limiter Unit Tests
=========================================
Tests for key extraction, storage URI resolution, and degradation
detection in app/core/rate_limit.py.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from starlette.requests import Request as StarletteRequest

from app.core.rate_limit import (
    RATE_LIMIT_DEGRADED,
    _get_user_or_ip,
    _resolve_storage_uri,
    limiter,
)

# ── _get_user_or_ip ───────────────────────────────────────────


def _make_request(user: object = None, client_host: str = "127.0.0.1") -> StarletteRequest:
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "client": (client_host, 1234),
    }
    request = StarletteRequest(scope)
    if user is not None:
        request.state.user = user
    return request


def test_get_user_or_ip_returns_user_id_when_authenticated() -> None:
    import uuid

    user = MagicMock()
    user.id = uuid.UUID("12345678-1234-5678-1234-567812345678")
    request = _make_request(user=user)

    key = _get_user_or_ip(request)

    assert key == f"user:{user.id}"


def test_get_user_or_ip_returns_ip_when_no_user() -> None:
    request = _make_request(user=None, client_host="10.0.0.1")
    key = _get_user_or_ip(request)
    assert key == "10.0.0.1"


def test_get_user_or_ip_returns_ip_when_user_has_no_id() -> None:
    user = MagicMock(spec=[])  # no 'id' attribute
    request = _make_request(user=user, client_host="192.168.1.1")
    key = _get_user_or_ip(request)
    assert key == "192.168.1.1"


def test_get_user_or_ip_unauthenticated_state() -> None:
    """Request with no state.user attribute falls back to IP."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
        "client": ("8.8.8.8", 80),
    }
    request = StarletteRequest(scope)
    key = _get_user_or_ip(request)
    assert key == "8.8.8.8"


# ── _resolve_storage_uri ──────────────────────────────────────


def test_resolve_storage_uri_returns_explicit_config() -> None:
    from app.core.config import settings

    original_uri = settings.ratelimit_storage_uri
    original_redis = settings.redis_url
    object.__setattr__(settings, "ratelimit_storage_uri", "redis://explicit:6379/0")
    object.__setattr__(settings, "redis_url", "")
    try:
        uri = _resolve_storage_uri()
    finally:
        object.__setattr__(settings, "ratelimit_storage_uri", original_uri)
        object.__setattr__(settings, "redis_url", original_redis)

    assert uri == "redis://explicit:6379/0"


def test_resolve_storage_uri_memory_when_no_redis() -> None:
    from app.core.config import settings

    original_uri = settings.ratelimit_storage_uri
    original_redis = settings.redis_url
    object.__setattr__(settings, "ratelimit_storage_uri", "memory://")
    object.__setattr__(settings, "redis_url", "")
    try:
        uri = _resolve_storage_uri()
    finally:
        object.__setattr__(settings, "ratelimit_storage_uri", original_uri)
        object.__setattr__(settings, "redis_url", original_redis)

    assert uri == "memory://"


def test_resolve_storage_uri_auto_configures_redis_when_available() -> None:
    from app.core.config import settings

    original_uri = settings.ratelimit_storage_uri
    original_redis = settings.redis_url

    object.__setattr__(settings, "ratelimit_storage_uri", "memory://")
    object.__setattr__(settings, "redis_url", "redis://localhost:6379")

    mock_client = MagicMock()
    mock_client.ping.return_value = True

    try:
        with patch("redis.Redis.from_url", return_value=mock_client), \
             patch(
                 "app.core.redis_ssl.resolve_redis_url",
                 return_value="redis://localhost:6379",
             ):
            uri = _resolve_storage_uri()
    finally:
        object.__setattr__(settings, "ratelimit_storage_uri", original_uri)
        object.__setattr__(settings, "redis_url", original_redis)

    assert "redis" in uri


def test_resolve_storage_uri_falls_back_to_memory_on_redis_error() -> None:
    from app.core.config import settings

    original_uri = settings.ratelimit_storage_uri
    original_redis = settings.redis_url
    object.__setattr__(settings, "ratelimit_storage_uri", "memory://")
    object.__setattr__(settings, "redis_url", "redis://localhost:6379")

    try:
        with patch("redis.Redis.from_url", side_effect=ConnectionError("no redis")), \
             patch(
                 "app.core.redis_ssl.resolve_redis_url",
                 return_value="redis://localhost:6379",
             ):
            uri = _resolve_storage_uri()
    finally:
        object.__setattr__(settings, "ratelimit_storage_uri", original_uri)
        object.__setattr__(settings, "redis_url", original_redis)

    assert uri == "memory://"


# ── RATE_LIMIT_DEGRADED ───────────────────────────────────────


def test_rate_limit_degraded_is_bool() -> None:
    assert isinstance(RATE_LIMIT_DEGRADED, bool)


# ── limiter instance ──────────────────────────────────────────


def test_limiter_is_initialized() -> None:
    assert limiter is not None
