"""
Tests for app.core.rate_limit module.

Covers:
- _get_user_or_ip key resolution (user vs IP fallback)
- _resolve_storage_uri with configured URI, Redis available, Redis failure, no Redis
- RATE_LIMIT_DEGRADED flag semantics
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.core import rate_limit


class TestGetUserOrIp:
    """Tests for _get_user_or_ip key resolution."""

    def test_authenticated_user_returns_user_key(self):
        request = MagicMock()
        request.state.user = MagicMock()
        request.state.user.id = "user-uuid-123"

        result = rate_limit._get_user_or_ip(request)

        assert result == "user:user-uuid-123"

    def test_no_user_state_falls_back_to_ip(self):
        request = MagicMock()
        # Simulate no user attribute on request.state
        request.state = MagicMock(spec=[])

        with patch(
            "app.core.rate_limit.get_remote_address",
            return_value="192.168.1.42",
        ) as mock_remote:
            result = rate_limit._get_user_or_ip(request)

        assert result == "192.168.1.42"
        mock_remote.assert_called_once_with(request)

    def test_user_without_id_falls_back_to_ip(self):
        request = MagicMock()
        # User exists but has no 'id' attribute
        request.state.user = MagicMock(spec=[])

        with patch(
            "app.core.rate_limit.get_remote_address",
            return_value="10.0.0.1",
        ) as mock_remote:
            result = rate_limit._get_user_or_ip(request)

        assert result == "10.0.0.1"
        mock_remote.assert_called_once_with(request)

    def test_user_is_none_falls_back_to_ip(self):
        request = MagicMock()
        request.state.user = None

        with patch(
            "app.core.rate_limit.get_remote_address",
            return_value="127.0.0.1",
        ):
            result = rate_limit._get_user_or_ip(request)

        assert result == "127.0.0.1"

    def test_user_id_stringified_in_key(self):
        request = MagicMock()
        request.state.user = MagicMock()
        request.state.user.id = 42  # non-string id

        result = rate_limit._get_user_or_ip(request)

        assert result == "user:42"


class TestResolveStorageUri:
    """Tests for _resolve_storage_uri failover logic."""

    def test_configured_non_default_uri_returned_as_is(self):
        with patch.object(
            rate_limit.settings,
            "ratelimit_storage_uri",
            "redis://explicit:6379/0",
        ):
            result = rate_limit._resolve_storage_uri()

        assert result == "redis://explicit:6379/0"

    def test_redis_url_with_successful_ping_returns_resolved_url(self):
        mock_client = MagicMock()
        mock_client.ping.return_value = True

        with (
            patch.object(rate_limit.settings, "ratelimit_storage_uri", "memory://"),
            patch.object(
                rate_limit.settings, "redis_url", "redis://localhost:6379/0"
            ),
            patch.object(rate_limit.settings, "environment", "test"),
            patch(
                "app.core.redis_ssl.resolve_redis_url",
                return_value="redis://localhost:6379/0",
            ) as mock_resolve,
            patch("redis.Redis.from_url", return_value=mock_client) as mock_from_url,
        ):
            result = rate_limit._resolve_storage_uri()

        assert result == "redis://localhost:6379/0"
        mock_resolve.assert_called_once_with(
            "redis://localhost:6379/0", False, "test"
        )
        mock_from_url.assert_called_once()
        mock_client.ping.assert_called_once()
        mock_client.close.assert_called_once()

    def test_redis_url_with_ping_failure_falls_back_to_memory(self):
        mock_client = MagicMock()
        mock_client.ping.side_effect = ConnectionError("Redis is down")

        with (
            patch.object(rate_limit.settings, "ratelimit_storage_uri", "memory://"),
            patch.object(
                rate_limit.settings, "redis_url", "redis://localhost:6379/0"
            ),
            patch.object(rate_limit.settings, "environment", "test"),
            patch(
                "app.core.redis_ssl.resolve_redis_url",
                return_value="redis://localhost:6379/0",
            ),
            patch("redis.Redis.from_url", return_value=mock_client),
        ):
            result = rate_limit._resolve_storage_uri()

        assert result == "memory://"

    def test_redis_from_url_raises_falls_back_to_memory(self):
        with (
            patch.object(rate_limit.settings, "ratelimit_storage_uri", "memory://"),
            patch.object(
                rate_limit.settings, "redis_url", "redis://localhost:6379/0"
            ),
            patch.object(rate_limit.settings, "environment", "test"),
            patch(
                "app.core.redis_ssl.resolve_redis_url",
                return_value="redis://localhost:6379/0",
            ),
            patch(
                "redis.Redis.from_url",
                side_effect=Exception("Connection refused"),
            ),
        ):
            result = rate_limit._resolve_storage_uri()

        assert result == "memory://"

    def test_no_redis_url_returns_memory(self):
        with (
            patch.object(rate_limit.settings, "ratelimit_storage_uri", "memory://"),
            patch.object(rate_limit.settings, "redis_url", None),
        ):
            result = rate_limit._resolve_storage_uri()

        assert result == "memory://"

    def test_empty_redis_url_returns_memory(self):
        with (
            patch.object(rate_limit.settings, "ratelimit_storage_uri", "memory://"),
            patch.object(rate_limit.settings, "redis_url", ""),
        ):
            result = rate_limit._resolve_storage_uri()

        assert result == "memory://"

    def test_empty_configured_uri_with_no_redis_returns_empty(self):
        # When configured_uri is empty string (falsy) and no redis_url,
        # the function returns configured_uri as-is.
        with (
            patch.object(rate_limit.settings, "ratelimit_storage_uri", ""),
            patch.object(rate_limit.settings, "redis_url", None),
        ):
            result = rate_limit._resolve_storage_uri()

        assert result == ""


class TestRateLimitDegraded:
    """Tests for RATE_LIMIT_DEGRADED flag semantics."""

    def test_degraded_flag_is_bool(self):
        assert isinstance(rate_limit.RATE_LIMIT_DEGRADED, bool)

    def test_degraded_false_when_no_redis_configured(self):
        # Recompute the flag under controlled settings: no redis_url means
        # we're not in "degraded" mode even when memory:// is used.
        with (
            patch.object(rate_limit.settings, "ratelimit_storage_uri", "memory://"),
            patch.object(rate_limit.settings, "redis_url", None),
        ):
            resolved = rate_limit._resolve_storage_uri()
            degraded = resolved == "memory://" and bool(
                rate_limit.settings.redis_url
            )

        assert resolved == "memory://"
        assert degraded is False

    def test_degraded_true_when_redis_configured_but_memory_used(self):
        # Simulate Redis URL present but connectivity check failing.
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("unreachable")

        with (
            patch.object(rate_limit.settings, "ratelimit_storage_uri", "memory://"),
            patch.object(
                rate_limit.settings, "redis_url", "redis://localhost:6379/0"
            ),
            patch.object(rate_limit.settings, "environment", "test"),
            patch(
                "app.core.redis_ssl.resolve_redis_url",
                return_value="redis://localhost:6379/0",
            ),
            patch("redis.Redis.from_url", return_value=mock_client),
        ):
            resolved = rate_limit._resolve_storage_uri()
            degraded = resolved == "memory://" and bool(
                rate_limit.settings.redis_url
            )

        assert resolved == "memory://"
        assert degraded is True


class TestLimiterInstance:
    """Smoke tests for the configured limiter instance."""

    def test_limiter_exists(self):
        assert rate_limit.limiter is not None

    def test_limiter_uses_user_or_ip_key_func(self):
        assert rate_limit.limiter._key_func is rate_limit._get_user_or_ip
