"""
PathForge — Push Notification Service Tests
============================================
Comprehensive unit tests for app.services.push_service covering:
    - mask_token (pure function)
    - get_http_client / close_http_client (lifecycle)
    - dispatch (main pipeline + early returns)
    - register_token / deregister_token / get_status
    - _in_quiet_hours / _get_daily_push_count / _build_payload
    - _increment_dispatch_count
    - _send_to_token via dispatch (410, 4xx, 5xx, retries)

Target: 85%+ coverage. Ruff-clean (SIM117 combined with-statements).
"""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.services import push_service
from app.services.push_service import (
    MAX_PUSH_PER_DAY,
    MAX_RETRY_ATTEMPTS,
    _build_payload,
    _get_daily_push_count,
    _in_quiet_hours,
    _increment_dispatch_count,
    close_http_client,
    deregister_token,
    dispatch,
    get_http_client,
    get_status,
    mask_token,
    register_token,
)

pytestmark = pytest.mark.asyncio


# ── Helpers ────────────────────────────────────────────────────


def _make_pref(
    *,
    push_notifications: bool = True,
    quiet_start: time | None = None,
    quiet_end: time | None = None,
    daily_push_count: int = 0,
    last_push_date: date | None = None,
) -> MagicMock:
    """Build a mock NotificationPreference with sane defaults."""
    pref = MagicMock()
    pref.push_notifications = push_notifications
    pref.quiet_hours_start = quiet_start
    pref.quiet_hours_end = quiet_end
    pref.daily_push_count = daily_push_count
    pref.last_push_date = last_push_date
    return pref


def _make_notification(
    *,
    user_id: str | None = None,
    title: str = "Hello",
    body: str = "World",
    severity: str = "normal",
    notification_type: str = "career_insight",
    action_url: str | None = "https://example.com/foo",
) -> MagicMock:
    """Build a mock CareerNotification."""
    notif = MagicMock()
    notif.id = uuid.uuid4()
    notif.user_id = user_id or str(uuid.uuid4())
    notif.title = title
    notif.body = body
    notif.severity = severity
    notif.notification_type = notification_type
    notif.action_url = action_url
    return notif


def _make_token(
    *,
    device_token: str = "ExponentPushToken[abcdefgh]",
    is_active: bool = True,
    platform: str = "ios",
    user_id: str | None = None,
) -> MagicMock:
    """Build a mock PushToken."""
    tok = MagicMock()
    tok.device_token = device_token
    tok.is_active = is_active
    tok.platform = platform
    tok.user_id = user_id or str(uuid.uuid4())
    tok.last_used_at = None
    return tok


def _mock_db_with_results(results: list) -> MagicMock:
    """Build a MagicMock db session that returns `results` from execute().

    Each result in `results` is the object returned from `execute()`
    for successive calls — emulating multiple queries in sequence.
    """
    db = MagicMock()
    db.execute = AsyncMock(side_effect=results)
    db.flush = AsyncMock()
    db.add = MagicMock()
    return db


def _scalar_result(value):
    """Build an execute() return value whose scalar_one_or_none() yields `value`."""
    result = MagicMock()
    result.scalar_one_or_none = MagicMock(return_value=value)
    return result


def _scalars_result(values: list):
    """Build an execute() return value whose scalars().all() yields `values`."""
    result = MagicMock()
    scalars = MagicMock()
    scalars.all = MagicMock(return_value=values)
    result.scalars = MagicMock(return_value=scalars)
    return result


def _rowcount_result(rowcount: int):
    """Build an execute() return value with .rowcount."""
    result = MagicMock()
    result.rowcount = rowcount
    return result


# ── mask_token ─────────────────────────────────────────────────


class TestMaskToken:
    """Pure function — last-4 masking with short-token safety."""

    def test_short_token_returns_stars(self) -> None:
        assert mask_token("abc") == "***"

    def test_empty_token_returns_stars(self) -> None:
        assert mask_token("") == "***"

    def test_exactly_four_chars_returns_stars(self) -> None:
        assert mask_token("abcd") == "***"

    def test_five_chars_reveals_last_four(self) -> None:
        assert mask_token("abcde") == "***bcde"

    def test_normal_token_reveals_last_four(self) -> None:
        token = "ExponentPushToken[abc123xyz]"
        assert mask_token(token) == "***xyz]"

    def test_very_long_token(self) -> None:
        token = "x" * 200 + "last"
        assert mask_token(token) == "***last"


# ── _in_quiet_hours ───────────────────────────────────────────


class TestInQuietHours:
    """Pure function — supports none / same-day / overnight ranges."""

    def test_no_quiet_hours_returns_false(self) -> None:
        pref = _make_pref(quiet_start=None, quiet_end=None)
        assert _in_quiet_hours(pref) is False

    def test_only_start_set_returns_false(self) -> None:
        pref = _make_pref(quiet_start=time(22, 0), quiet_end=None)
        assert _in_quiet_hours(pref) is False

    def test_only_end_set_returns_false(self) -> None:
        pref = _make_pref(quiet_start=None, quiet_end=time(7, 0))
        assert _in_quiet_hours(pref) is False

    def test_same_day_range_in_quiet(self) -> None:
        pref = _make_pref(quiet_start=time(9, 0), quiet_end=time(17, 0))
        fake_now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
        with patch("app.services.push_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            assert _in_quiet_hours(pref) is True

    def test_same_day_range_before_quiet(self) -> None:
        pref = _make_pref(quiet_start=time(9, 0), quiet_end=time(17, 0))
        fake_now = datetime(2026, 4, 24, 8, 0, tzinfo=UTC)
        with patch("app.services.push_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            assert _in_quiet_hours(pref) is False

    def test_same_day_range_after_quiet(self) -> None:
        pref = _make_pref(quiet_start=time(9, 0), quiet_end=time(17, 0))
        fake_now = datetime(2026, 4, 24, 18, 0, tzinfo=UTC)
        with patch("app.services.push_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            assert _in_quiet_hours(pref) is False

    def test_overnight_range_in_quiet_late_night(self) -> None:
        pref = _make_pref(quiet_start=time(22, 0), quiet_end=time(7, 0))
        fake_now = datetime(2026, 4, 24, 23, 30, tzinfo=UTC)
        with patch("app.services.push_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            assert _in_quiet_hours(pref) is True

    def test_overnight_range_in_quiet_early_morning(self) -> None:
        pref = _make_pref(quiet_start=time(22, 0), quiet_end=time(7, 0))
        fake_now = datetime(2026, 4, 24, 3, 0, tzinfo=UTC)
        with patch("app.services.push_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            assert _in_quiet_hours(pref) is True

    def test_overnight_range_out_of_quiet(self) -> None:
        pref = _make_pref(quiet_start=time(22, 0), quiet_end=time(7, 0))
        fake_now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
        with patch("app.services.push_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            assert _in_quiet_hours(pref) is False

    def test_overnight_range_boundary_start(self) -> None:
        pref = _make_pref(quiet_start=time(22, 0), quiet_end=time(7, 0))
        fake_now = datetime(2026, 4, 24, 22, 0, tzinfo=UTC)
        with patch("app.services.push_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            assert _in_quiet_hours(pref) is True

    def test_overnight_range_boundary_end(self) -> None:
        pref = _make_pref(quiet_start=time(22, 0), quiet_end=time(7, 0))
        fake_now = datetime(2026, 4, 24, 7, 0, tzinfo=UTC)
        with patch("app.services.push_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            assert _in_quiet_hours(pref) is True


# ── _get_daily_push_count ─────────────────────────────────────


class TestGetDailyPushCount:
    """Pure function — reset counter when day changes."""

    def test_returns_count_when_date_matches_today(self) -> None:
        pref = _make_pref(daily_push_count=2, last_push_date=date.today())
        assert _get_daily_push_count(pref) == 2

    def test_returns_zero_when_date_is_yesterday(self) -> None:
        pref = _make_pref(
            daily_push_count=10,
            last_push_date=date.today() - timedelta(days=1),
        )
        assert _get_daily_push_count(pref) == 0

    def test_returns_zero_when_date_is_none(self) -> None:
        pref = _make_pref(daily_push_count=5, last_push_date=None)
        assert _get_daily_push_count(pref) == 0

    def test_returns_zero_when_date_is_future(self) -> None:
        pref = _make_pref(
            daily_push_count=3,
            last_push_date=date.today() + timedelta(days=1),
        )
        assert _get_daily_push_count(pref) == 0


# ── _build_payload ────────────────────────────────────────────


class TestBuildPayload:
    """Pure function — builds Expo payload with severity-based priority."""

    def test_normal_severity_sets_normal_priority(self) -> None:
        notif = _make_notification(severity="normal")
        payload = _build_payload(notif)
        assert payload["priority"] == "normal"

    def test_info_severity_sets_normal_priority(self) -> None:
        notif = _make_notification(severity="info")
        payload = _build_payload(notif)
        assert payload["priority"] == "normal"

    def test_critical_severity_sets_high_priority(self) -> None:
        notif = _make_notification(severity="critical")
        payload = _build_payload(notif)
        assert payload["priority"] == "high"

    def test_high_severity_sets_high_priority(self) -> None:
        notif = _make_notification(severity="high")
        payload = _build_payload(notif)
        assert payload["priority"] == "high"

    def test_payload_includes_title_and_body(self) -> None:
        notif = _make_notification(title="Hi", body="Body text")
        payload = _build_payload(notif)
        assert payload["title"] == "Hi"
        assert payload["body"] == "Body text"

    def test_body_truncated_at_200_chars(self) -> None:
        long_body = "x" * 300
        notif = _make_notification(body=long_body)
        payload = _build_payload(notif)
        assert len(payload["body"]) == 200
        assert payload["body"] == "x" * 200

    def test_body_at_exactly_200_chars_not_truncated(self) -> None:
        body = "x" * 200
        notif = _make_notification(body=body)
        payload = _build_payload(notif)
        assert payload["body"] == body

    def test_empty_body_returns_empty_string(self) -> None:
        notif = _make_notification(body="")
        payload = _build_payload(notif)
        assert payload["body"] == ""

    def test_none_body_returns_empty_string(self) -> None:
        notif = _make_notification()
        notif.body = None
        payload = _build_payload(notif)
        assert payload["body"] == ""

    def test_data_includes_notification_metadata(self) -> None:
        notif = _make_notification(
            notification_type="goal_progress",
            severity="critical",
            action_url="https://example.com/goals",
        )
        payload = _build_payload(notif)
        assert payload["data"]["notification_id"] == str(notif.id)
        assert payload["data"]["type"] == "goal_progress"
        assert payload["data"]["severity"] == "critical"
        assert payload["data"]["action_url"] == "https://example.com/goals"

    def test_none_action_url_becomes_empty_string(self) -> None:
        notif = _make_notification(action_url=None)
        payload = _build_payload(notif)
        assert payload["data"]["action_url"] == ""

    def test_sound_is_default(self) -> None:
        notif = _make_notification()
        payload = _build_payload(notif)
        assert payload["sound"] == "default"


# ── get_http_client / close_http_client ───────────────────────


class TestHttpClientLifecycle:
    """Singleton lifecycle for shared Expo HTTP client."""

    async def test_creates_new_client_when_none(self) -> None:
        push_service._http_client = None
        try:
            client = await get_http_client()
            assert client is not None
            assert isinstance(client, httpx.AsyncClient)
        finally:
            await close_http_client()

    async def test_reuses_open_client(self) -> None:
        push_service._http_client = None
        try:
            client1 = await get_http_client()
            client2 = await get_http_client()
            assert client1 is client2
        finally:
            await close_http_client()

    async def test_creates_new_when_closed(self) -> None:
        push_service._http_client = None
        try:
            client1 = await get_http_client()
            await client1.aclose()
            client2 = await get_http_client()
            assert client2 is not client1
            assert not client2.is_closed
        finally:
            await close_http_client()

    async def test_close_closes_open_client(self) -> None:
        push_service._http_client = None
        client = await get_http_client()
        assert not client.is_closed
        await close_http_client()
        assert push_service._http_client is None

    async def test_close_is_noop_when_none(self) -> None:
        push_service._http_client = None
        # Should not raise.
        await close_http_client()
        assert push_service._http_client is None

    async def test_close_is_noop_when_already_closed(self) -> None:
        push_service._http_client = None
        client = await get_http_client()
        await client.aclose()
        # Already-closed client: close_http_client skips aclose branch.
        await close_http_client()
        # Singleton was never cleared because the branch was skipped.
        assert push_service._http_client is client
        # Reset for isolation.
        push_service._http_client = None


# ── dispatch (early-return paths) ─────────────────────────────


class TestDispatchEarlyReturns:
    """Pipeline short-circuits before hitting HTTP client."""

    async def test_pref_is_none_returns_early(self) -> None:
        db = _mock_db_with_results([_scalar_result(None)])
        notif = _make_notification()
        await dispatch(db, notification=notif)
        # Only the preference query should have run.
        assert db.execute.await_count == 1

    async def test_push_disabled_returns_early(self) -> None:
        pref = _make_pref(push_notifications=False)
        db = _mock_db_with_results([_scalar_result(pref)])
        notif = _make_notification()
        await dispatch(db, notification=notif)
        assert db.execute.await_count == 1

    async def test_in_quiet_hours_returns_early(self) -> None:
        pref = _make_pref(
            quiet_start=time(0, 0),
            quiet_end=time(23, 59, 59),
        )
        db = _mock_db_with_results([_scalar_result(pref)])
        notif = _make_notification()
        fake_now = datetime(2026, 4, 24, 12, 0, tzinfo=UTC)
        with patch("app.services.push_service.datetime") as mock_dt:
            mock_dt.now.return_value = fake_now
            await dispatch(db, notification=notif)
        assert db.execute.await_count == 1

    async def test_daily_limit_exceeded_returns_early(self) -> None:
        pref = _make_pref(
            daily_push_count=MAX_PUSH_PER_DAY,
            last_push_date=date.today(),
        )
        db = _mock_db_with_results([_scalar_result(pref)])
        notif = _make_notification()
        await dispatch(db, notification=notif)
        assert db.execute.await_count == 1

    async def test_no_active_tokens_returns_early(self) -> None:
        pref = _make_pref()
        db = _mock_db_with_results([
            _scalar_result(pref),
            _scalars_result([]),
        ])
        notif = _make_notification()
        await dispatch(db, notification=notif)
        assert db.execute.await_count == 2
        # No increment — no flush() triggered for counter.
        db.flush.assert_not_awaited()

    async def test_exception_caught_silently(self) -> None:
        db = MagicMock()
        db.execute = AsyncMock(side_effect=RuntimeError("boom"))
        db.flush = AsyncMock()
        notif = _make_notification()
        # Must not raise.
        await dispatch(db, notification=notif)


# ── dispatch (successful paths hitting _send_to_token) ────────


class TestDispatchSuccess:
    """Full pipeline mocking Expo HTTP calls."""

    async def test_successful_dispatch_posts_to_expo(self) -> None:
        pref = _make_pref()
        token = _make_token()
        db = _mock_db_with_results([
            _scalar_result(pref),
            _scalars_result([token]),
        ])
        notif = _make_notification()

        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=response)

        with (
            patch(
                "app.services.push_service.get_http_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.push_service.asyncio.sleep",
                new=AsyncMock(),
            ),
        ):
            await dispatch(db, notification=notif)

        mock_client.post.assert_awaited_once()
        call = mock_client.post.call_args
        assert call.args[0] == push_service.EXPO_PUSH_URL
        assert call.kwargs["json"]["to"] == token.device_token
        # Counter incremented.
        assert pref.daily_push_count == 1

    async def test_410_deactivates_token(self) -> None:
        pref = _make_pref()
        token = _make_token(is_active=True)
        db = _mock_db_with_results([
            _scalar_result(pref),
            _scalars_result([token]),
        ])
        notif = _make_notification()

        response = MagicMock()
        response.status_code = 410
        response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=response)

        with (
            patch(
                "app.services.push_service.get_http_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.push_service.asyncio.sleep",
                new=AsyncMock(),
            ),
        ):
            await dispatch(db, notification=notif)

        assert token.is_active is False
        # Still counts as a dispatch attempt (increment runs after loop).
        assert pref.daily_push_count == 1

    async def test_client_error_4xx_no_retry(self) -> None:
        pref = _make_pref()
        token = _make_token()
        db = _mock_db_with_results([
            _scalar_result(pref),
            _scalars_result([token]),
        ])
        notif = _make_notification()

        err_response = MagicMock()
        err_response.status_code = 400
        exc = httpx.HTTPStatusError(
            "bad request", request=MagicMock(), response=err_response,
        )

        response = MagicMock()
        response.status_code = 400
        response.raise_for_status = MagicMock(side_effect=exc)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=response)

        sleep_mock = AsyncMock()
        with (
            patch(
                "app.services.push_service.get_http_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch("app.services.push_service.asyncio.sleep", new=sleep_mock),
        ):
            await dispatch(db, notification=notif)

        # Only one POST — no retries on 4xx.
        assert mock_client.post.await_count == 1
        sleep_mock.assert_not_awaited()

    async def test_server_error_5xx_retries_up_to_max(self) -> None:
        pref = _make_pref()
        token = _make_token()
        db = _mock_db_with_results([
            _scalar_result(pref),
            _scalars_result([token]),
        ])
        notif = _make_notification()

        err_response = MagicMock()
        err_response.status_code = 503
        exc = httpx.HTTPStatusError(
            "server error", request=MagicMock(), response=err_response,
        )

        response = MagicMock()
        response.status_code = 503
        response.raise_for_status = MagicMock(side_effect=exc)

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=response)

        sleep_mock = AsyncMock()
        with (
            patch(
                "app.services.push_service.get_http_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch("app.services.push_service.asyncio.sleep", new=sleep_mock),
        ):
            await dispatch(db, notification=notif)

        assert mock_client.post.await_count == MAX_RETRY_ATTEMPTS
        # Sleep called MAX_RETRY_ATTEMPTS - 1 times (no sleep after last).
        assert sleep_mock.await_count == MAX_RETRY_ATTEMPTS - 1

    async def test_generic_exception_retries(self) -> None:
        pref = _make_pref()
        token = _make_token()
        db = _mock_db_with_results([
            _scalar_result(pref),
            _scalars_result([token]),
        ])
        notif = _make_notification()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(side_effect=RuntimeError("network down"))

        sleep_mock = AsyncMock()
        with (
            patch(
                "app.services.push_service.get_http_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch("app.services.push_service.asyncio.sleep", new=sleep_mock),
        ):
            await dispatch(db, notification=notif)

        assert mock_client.post.await_count == MAX_RETRY_ATTEMPTS
        assert sleep_mock.await_count == MAX_RETRY_ATTEMPTS - 1

    async def test_multiple_tokens_all_receive_push(self) -> None:
        pref = _make_pref()
        tok1 = _make_token(device_token="ExponentPushToken[aaa]")
        tok2 = _make_token(device_token="ExponentPushToken[bbb]")
        db = _mock_db_with_results([
            _scalar_result(pref),
            _scalars_result([tok1, tok2]),
        ])
        notif = _make_notification()

        response = MagicMock()
        response.status_code = 200
        response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post = AsyncMock(return_value=response)

        with (
            patch(
                "app.services.push_service.get_http_client",
                new=AsyncMock(return_value=mock_client),
            ),
            patch(
                "app.services.push_service.asyncio.sleep",
                new=AsyncMock(),
            ),
        ):
            await dispatch(db, notification=notif)

        assert mock_client.post.await_count == 2


# ── register_token ────────────────────────────────────────────


class TestRegisterToken:
    """Idempotent upsert — reassigns token across users."""

    async def test_creates_new_token_when_missing(self) -> None:
        db = _mock_db_with_results([_scalar_result(None)])
        user_id = uuid.uuid4()

        result = await register_token(
            db,
            user_id=user_id,
            device_token="ExponentPushToken[new]",
            platform="ios",
        )

        db.add.assert_called_once()
        db.flush.assert_awaited_once()
        assert result.device_token == "ExponentPushToken[new]"
        assert result.user_id == str(user_id)
        assert result.platform == "ios"
        assert result.is_active is True

    async def test_reactivates_existing_token(self) -> None:
        existing = _make_token(is_active=False, platform="android")
        existing.user_id = "old-user"
        db = _mock_db_with_results([_scalar_result(existing)])

        new_user_id = uuid.uuid4()
        result = await register_token(
            db,
            user_id=new_user_id,
            device_token=existing.device_token,
            platform="ios",
        )

        assert result is existing
        assert existing.user_id == str(new_user_id)
        assert existing.platform == "ios"
        assert existing.is_active is True
        assert isinstance(existing.last_used_at, datetime)
        db.add.assert_not_called()
        db.flush.assert_awaited_once()


# ── deregister_token ──────────────────────────────────────────


class TestDeregisterToken:
    """Ownership-scoped deactivation — returns bool."""

    async def test_returns_true_when_found(self) -> None:
        db = _mock_db_with_results([_rowcount_result(1)])
        user_id = uuid.uuid4()

        ok = await deregister_token(
            db,
            user_id=user_id,
            device_token="ExponentPushToken[abc]",
        )
        assert ok is True

    async def test_returns_false_when_not_found(self) -> None:
        db = _mock_db_with_results([_rowcount_result(0)])
        user_id = uuid.uuid4()

        ok = await deregister_token(
            db,
            user_id=user_id,
            device_token="ExponentPushToken[missing]",
        )
        assert ok is False


# ── get_status ────────────────────────────────────────────────


class TestGetStatus:
    """Masked-token status response."""

    async def test_returns_unregistered_when_no_token(self) -> None:
        db = _mock_db_with_results([_scalar_result(None)])
        user_id = uuid.uuid4()

        status = await get_status(db, user_id=user_id)
        assert status == {"registered": False, "token": None, "platform": None}

    async def test_returns_masked_token_when_registered(self) -> None:
        token = _make_token(
            device_token="ExponentPushToken[zzz1234]",
            platform="android",
        )
        db = _mock_db_with_results([_scalar_result(token)])
        user_id = uuid.uuid4()

        status = await get_status(db, user_id=user_id)
        assert status["registered"] is True
        assert status["platform"] == "android"
        # mask_token reveals last 4 only.
        assert status["token"].startswith("***")
        assert status["token"].endswith("234]")


# ── _increment_dispatch_count ─────────────────────────────────


class TestIncrementDispatchCount:
    """Counter reset on new day, increment otherwise."""

    async def test_resets_on_new_day(self) -> None:
        pref = _make_pref(
            daily_push_count=5,
            last_push_date=date.today() - timedelta(days=1),
        )
        db = _mock_db_with_results([])

        await _increment_dispatch_count(db, pref=pref)
        assert pref.daily_push_count == 1
        assert pref.last_push_date == date.today()
        db.flush.assert_awaited_once()

    async def test_resets_when_last_date_is_none(self) -> None:
        pref = _make_pref(daily_push_count=99, last_push_date=None)
        db = _mock_db_with_results([])

        await _increment_dispatch_count(db, pref=pref)
        assert pref.daily_push_count == 1
        assert pref.last_push_date == date.today()

    async def test_increments_on_same_day(self) -> None:
        pref = _make_pref(daily_push_count=2, last_push_date=date.today())
        db = _mock_db_with_results([])

        await _increment_dispatch_count(db, pref=pref)
        assert pref.daily_push_count == 3
        assert pref.last_push_date == date.today()
        db.flush.assert_awaited_once()

    async def test_increment_from_zero_same_day(self) -> None:
        pref = _make_pref(daily_push_count=0, last_push_date=date.today())
        db = _mock_db_with_results([])

        await _increment_dispatch_count(db, pref=pref)
        assert pref.daily_push_count == 1
