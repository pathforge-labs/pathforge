"""
PathForge — Token Blacklist Unit Tests
=========================================
Tests for Redis-backed JWT revocation in app/core/token_blacklist.py.
Redis calls are mocked via AsyncMock.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.token_blacklist import TokenBlacklist, token_blacklist

# ── Fixtures ──────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_redis() -> None:  # type: ignore[misc]
    """Reset the cached Redis connection before each test."""
    TokenBlacklist._redis = None
    yield
    TokenBlacklist._redis = None


def _make_redis() -> AsyncMock:
    """Create a mock async Redis client."""
    r = AsyncMock()
    r.setex = AsyncMock(return_value=True)
    r.set = AsyncMock(return_value=True)
    r.exists = AsyncMock(return_value=0)
    r.aclose = AsyncMock()
    return r


# ── get_redis: lazy initialisation ───────────────────────────


@pytest.mark.asyncio
async def test_get_redis_creates_connection() -> None:
    mock_redis = _make_redis()

    with patch("app.core.token_blacklist.Redis") as mock_redis_cls, \
         patch(
             "app.core.redis_ssl.resolve_redis_url",
             return_value="redis://localhost",
         ):
        mock_redis_cls.from_url.return_value = mock_redis
        redis = await TokenBlacklist.get_redis()

    assert redis is mock_redis
    assert TokenBlacklist._redis is mock_redis


@pytest.mark.asyncio
async def test_get_redis_reuses_existing_connection() -> None:
    mock_redis = _make_redis()
    TokenBlacklist._redis = mock_redis

    with patch("app.core.token_blacklist.Redis.from_url") as mock_from_url:
        redis = await TokenBlacklist.get_redis()

    assert redis is mock_redis
    mock_from_url.assert_not_called()


# ── revoke ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_revoke_calls_setex() -> None:
    mock_redis = _make_redis()
    TokenBlacklist._redis = mock_redis

    await TokenBlacklist.revoke(jti="abc-123", ttl_seconds=3600)

    mock_redis.setex.assert_awaited_once_with(
        "token:blacklist:abc-123", 3600, "revoked"
    )


@pytest.mark.asyncio
async def test_revoke_short_jti_logs_prefix() -> None:
    """revoke logs the first 8 chars of jti — works with short jtis too."""
    mock_redis = _make_redis()
    TokenBlacklist._redis = mock_redis

    await TokenBlacklist.revoke(jti="a", ttl_seconds=60)

    mock_redis.setex.assert_awaited_once()


# ── is_revoked ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_is_revoked_returns_true_when_key_exists() -> None:
    mock_redis = _make_redis()
    mock_redis.exists = AsyncMock(return_value=1)
    TokenBlacklist._redis = mock_redis

    result = await TokenBlacklist.is_revoked("abc-123")

    assert result is True
    mock_redis.exists.assert_awaited_once_with("token:blacklist:abc-123")


@pytest.mark.asyncio
async def test_is_revoked_returns_false_when_key_absent() -> None:
    mock_redis = _make_redis()
    mock_redis.exists = AsyncMock(return_value=0)
    TokenBlacklist._redis = mock_redis

    result = await TokenBlacklist.is_revoked("not-there")

    assert result is False


# ── consume_once ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_consume_once_first_call_returns_true() -> None:
    mock_redis = _make_redis()
    mock_redis.set = AsyncMock(return_value=True)  # nx=True succeeds
    TokenBlacklist._redis = mock_redis

    result = await TokenBlacklist.consume_once(jti="fresh-jti", ttl_seconds=1800)

    assert result is True
    mock_redis.set.assert_awaited_once_with(
        "token:blacklist:fresh-jti", "revoked", nx=True, ex=1800
    )


@pytest.mark.asyncio
async def test_consume_once_replay_returns_false() -> None:
    mock_redis = _make_redis()
    mock_redis.set = AsyncMock(return_value=None)  # nx=True fails — already exists
    TokenBlacklist._redis = mock_redis

    result = await TokenBlacklist.consume_once(jti="used-jti", ttl_seconds=1800)

    assert result is False


# ── close ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_close_calls_aclose_and_clears_ref() -> None:
    mock_redis = _make_redis()
    TokenBlacklist._redis = mock_redis

    await TokenBlacklist.close()

    mock_redis.aclose.assert_awaited_once()
    assert TokenBlacklist._redis is None


@pytest.mark.asyncio
async def test_close_noop_when_no_connection() -> None:
    TokenBlacklist._redis = None
    await TokenBlacklist.close()  # must not raise


# ── module-level convenience instance ────────────────────────


def test_module_level_instance_is_token_blacklist_class() -> None:
    assert token_blacklist is TokenBlacklist
