"""Tests for app.core.token_blacklist."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.token_blacklist import TokenBlacklist

_PREFIX = "token:blacklist:"


@pytest.fixture(autouse=True)
def _reset_redis() -> None:
    """Reset the TokenBlacklist class-level Redis singleton before each test."""
    TokenBlacklist._redis = None


@pytest.mark.asyncio
async def test_get_redis_creates_connection() -> None:
    """First call to get_redis should create a Redis instance via Redis.from_url."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://test"),
    ):
        mock_instance = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_instance

        result = await TokenBlacklist.get_redis()

        assert result is mock_instance
        mock_redis_cls.from_url.assert_called_once()


@pytest.mark.asyncio
async def test_get_redis_reuses_connection() -> None:
    """Second call to get_redis should return the cached instance."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://test"),
    ):
        mock_instance = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_instance

        first = await TokenBlacklist.get_redis()
        second = await TokenBlacklist.get_redis()

        assert first is second
        assert mock_redis_cls.from_url.call_count == 1


@pytest.mark.asyncio
async def test_get_redis_uses_resolve_redis_url() -> None:
    """get_redis should invoke resolve_redis_url with settings-derived args."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://resolved") as mock_resolve,
    ):
        mock_redis_cls.from_url.return_value = AsyncMock()

        await TokenBlacklist.get_redis()

        mock_resolve.assert_called_once()
        # Redis.from_url should receive the resolved URL as first positional arg
        args, kwargs = mock_redis_cls.from_url.call_args
        assert args[0] == "redis://resolved"
        assert kwargs.get("decode_responses") is True
        assert kwargs.get("socket_connect_timeout") == 5


@pytest.mark.asyncio
async def test_revoke_calls_setex() -> None:
    """revoke should call redis.setex with the prefixed key, TTL, and 'revoked'."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://test"),
    ):
        mock_instance = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_instance

        await TokenBlacklist.revoke(jti="abc-123", ttl_seconds=3600)

        mock_instance.setex.assert_awaited_once_with(
            f"{_PREFIX}abc-123", 3600, "revoked"
        )


@pytest.mark.asyncio
async def test_revoke_key_format() -> None:
    """Key format for revoke should be 'token:blacklist:{jti}'."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://test"),
    ):
        mock_instance = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_instance

        await TokenBlacklist.revoke(jti="jti-xyz", ttl_seconds=60)

        call_args = mock_instance.setex.await_args
        assert call_args.args[0] == "token:blacklist:jti-xyz"


@pytest.mark.asyncio
async def test_is_revoked_returns_true_when_exists() -> None:
    """is_revoked returns True when redis.exists returns a truthy count."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://test"),
    ):
        mock_instance = AsyncMock()
        mock_instance.exists = AsyncMock(return_value=1)
        mock_redis_cls.from_url.return_value = mock_instance

        result = await TokenBlacklist.is_revoked(jti="abc")

        assert result is True
        mock_instance.exists.assert_awaited_once_with(f"{_PREFIX}abc")


@pytest.mark.asyncio
async def test_is_revoked_returns_false_when_not_exists() -> None:
    """is_revoked returns False when redis.exists returns 0."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://test"),
    ):
        mock_instance = AsyncMock()
        mock_instance.exists = AsyncMock(return_value=0)
        mock_redis_cls.from_url.return_value = mock_instance

        result = await TokenBlacklist.is_revoked(jti="missing")

        assert result is False


@pytest.mark.asyncio
async def test_consume_once_returns_true_when_set() -> None:
    """consume_once returns True when redis.set NX succeeds (first consumer)."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://test"),
    ):
        mock_instance = AsyncMock()
        mock_instance.set = AsyncMock(return_value=True)
        mock_redis_cls.from_url.return_value = mock_instance

        result = await TokenBlacklist.consume_once(jti="one-shot", ttl_seconds=120)

        assert result is True
        mock_instance.set.assert_awaited_once_with(
            f"{_PREFIX}one-shot", "revoked", nx=True, ex=120
        )


@pytest.mark.asyncio
async def test_consume_once_returns_false_when_already_set() -> None:
    """consume_once returns False when redis.set NX returns None (replay)."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://test"),
    ):
        mock_instance = AsyncMock()
        mock_instance.set = AsyncMock(return_value=None)
        mock_redis_cls.from_url.return_value = mock_instance

        result = await TokenBlacklist.consume_once(jti="replay", ttl_seconds=60)

        assert result is False


@pytest.mark.asyncio
async def test_close_sets_redis_none() -> None:
    """After close(), the cached Redis instance should be None."""
    with (
        patch("app.core.token_blacklist.Redis") as mock_redis_cls,
        patch("app.core.redis_ssl.resolve_redis_url", return_value="redis://test"),
    ):
        mock_instance = AsyncMock()
        mock_redis_cls.from_url.return_value = mock_instance

        await TokenBlacklist.get_redis()
        assert TokenBlacklist._redis is mock_instance

        await TokenBlacklist.close()

        assert TokenBlacklist._redis is None
        mock_instance.aclose.assert_awaited_once()


@pytest.mark.asyncio
async def test_close_noop_when_not_connected() -> None:
    """Calling close() when no Redis instance exists should not raise."""
    assert TokenBlacklist._redis is None

    # Should simply be a no-op — no exception, no side effects.
    await TokenBlacklist.close()

    assert TokenBlacklist._redis is None
