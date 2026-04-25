"""Extended tests for UserService — new methods added in PR #14 (Phase 2 auth hardening).

Covers:
- ``_to_aware_utc`` helper
- ``UserService.reset_password_with_token`` (F30 atomic consume)
- ``UserService.resend_verification_if_eligible`` (F32 cooldown)
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.models.user import User
from app.services.email_service import generate_token
from app.services.user_service import UserService, _to_aware_utc
from app.services.user_service_errors import (
    ExpiredResetTokenError,
    InvalidResetTokenError,
    ResetTokenAlreadyUsedError,
)

# ── _to_aware_utc ─────────────────────────────────────────────────────────────


def test_to_aware_utc_naive_becomes_utc() -> None:
    naive = datetime(2026, 4, 25, 10, 0, 0)
    result = _to_aware_utc(naive)
    assert result.tzinfo is UTC
    assert result.replace(tzinfo=None) == naive


def test_to_aware_utc_already_aware_unchanged() -> None:
    aware = datetime(2026, 4, 25, 10, 0, 0, tzinfo=UTC)
    assert _to_aware_utc(aware) is aware


def test_to_aware_utc_non_utc_tz_preserved() -> None:
    cet = timezone(timedelta(hours=1))
    aware_cet = datetime(2026, 4, 25, 11, 0, 0, tzinfo=cet)
    result = _to_aware_utc(aware_cet)
    assert result is aware_cet


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_unverified_user(db: Any, email: str = "u@example.com") -> User:
    return await UserService.create_user(
        db,
        email=email,
        password="SecurePass1!",
        full_name="Test User",
    )


# ── reset_password_with_token ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_reset_password_unknown_token_raises(db_session: Any) -> None:
    with pytest.raises(InvalidResetTokenError):
        await UserService.reset_password_with_token(
            db_session,
            token="nosuchtoken",
            new_password="NewPass1!",
        )


@pytest.mark.asyncio
async def test_reset_password_missing_sent_at_raises(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "r-missing@example.com")
    raw, hashed = generate_token()
    user.password_reset_token = hashed
    user.password_reset_sent_at = None
    await db_session.flush()

    with pytest.raises(InvalidResetTokenError):
        await UserService.reset_password_with_token(
            db_session,
            token=raw,
            new_password="NewPass1!",
        )

    # Token should be scrubbed
    await db_session.refresh(user)
    assert user.password_reset_token is None


@pytest.mark.asyncio
async def test_reset_password_expired_token_raises(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "r-expired@example.com")
    raw, hashed = generate_token()
    user.password_reset_token = hashed
    user.password_reset_sent_at = datetime.now(UTC) - timedelta(hours=2)
    await db_session.flush()

    with pytest.raises(ExpiredResetTokenError):
        await UserService.reset_password_with_token(
            db_session,
            token=raw,
            new_password="NewPass1!",
        )

    # Token should be cleared after expiry check
    await db_session.refresh(user)
    assert user.password_reset_token is None
    assert user.password_reset_sent_at is None


@pytest.mark.asyncio
async def test_reset_password_success_updates_password(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "r-ok@example.com")
    raw, hashed = generate_token()
    user.password_reset_token = hashed
    user.password_reset_sent_at = datetime.now(UTC)
    await db_session.flush()

    await UserService.reset_password_with_token(
        db_session,
        token=raw,
        new_password="BrandNewPass1!",
    )

    await db_session.refresh(user)
    assert user.password_reset_token is None
    assert user.password_reset_sent_at is None
    assert user.tokens_invalidated_at is not None


@pytest.mark.asyncio
async def test_reset_password_clears_token_after_use(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "r-clear@example.com")
    raw, hashed = generate_token()
    user.password_reset_token = hashed
    user.password_reset_sent_at = datetime.now(UTC)
    await db_session.flush()

    await UserService.reset_password_with_token(
        db_session, token=raw, new_password="AnotherPass1!"
    )

    # Token must be gone — second attempt fails
    with pytest.raises(InvalidResetTokenError):
        await UserService.reset_password_with_token(
            db_session, token=raw, new_password="ThirdPass1!"
        )


@pytest.mark.asyncio
async def test_reset_password_race_rowcount_zero_raises(db_session: Any) -> None:
    """Simulates a concurrent request consuming the token first (rowcount=0)."""
    user = await _make_unverified_user(db_session, "r-race@example.com")
    raw, hashed = generate_token()
    user.password_reset_token = hashed
    user.password_reset_sent_at = datetime.now(UTC)
    await db_session.flush()

    # Let SELECT run normally; mock the UPDATE result to rowcount=0
    original_execute = db_session.execute
    call_count = 0

    async def selective_execute(stmt: Any, *args: Any, **kwargs: Any) -> Any:
        nonlocal call_count
        call_count += 1
        real = await original_execute(stmt, *args, **kwargs)
        if call_count == 2:  # UPDATE is the second execute call
            mock_res = MagicMock()
            mock_res.rowcount = 0
            return mock_res
        return real

    db_session.execute = selective_execute
    try:
        with pytest.raises(ResetTokenAlreadyUsedError):
            await UserService.reset_password_with_token(
                db_session, token=raw, new_password="RacedPass1!"
            )
    finally:
        db_session.execute = original_execute


# ── resend_verification_if_eligible ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_resend_verification_user_not_found_returns_false(db_session: Any) -> None:
    result = await UserService.resend_verification_if_eligible(
        db_session, email="nobody@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_resend_verification_inactive_user_returns_false(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "rv-inactive@example.com")
    user.is_active = False
    await db_session.flush()

    result = await UserService.resend_verification_if_eligible(
        db_session, email="rv-inactive@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_resend_verification_already_verified_returns_false(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "rv-verified@example.com")
    user.is_verified = True
    await db_session.flush()

    result = await UserService.resend_verification_if_eligible(
        db_session, email="rv-verified@example.com"
    )
    assert result is False


@pytest.mark.asyncio
async def test_resend_verification_no_prior_send_returns_true(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "rv-first@example.com")
    user.verification_sent_at = None
    user.verification_token = None
    await db_session.flush()

    with patch(
        "app.services.user_service.EmailService.send_verification_email"
    ) as email_mock:
        result = await UserService.resend_verification_if_eligible(
            db_session, email="rv-first@example.com"
        )

    assert result is True
    email_mock.assert_called_once()


@pytest.mark.asyncio
async def test_resend_verification_within_cooldown_returns_false(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "rv-cooldown@example.com")
    user.verification_sent_at = datetime.now(UTC)  # just now — inside cooldown
    await db_session.flush()

    with patch(
        "app.services.user_service.EmailService.send_verification_email"
    ) as email_mock:
        result = await UserService.resend_verification_if_eligible(
            db_session, email="rv-cooldown@example.com"
        )

    assert result is False
    email_mock.assert_not_called()


@pytest.mark.asyncio
async def test_resend_verification_past_cooldown_returns_true(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "rv-past@example.com")
    user.verification_sent_at = datetime.now(UTC) - timedelta(hours=1)
    await db_session.flush()

    with patch(
        "app.services.user_service.EmailService.send_verification_email"
    ) as email_mock:
        result = await UserService.resend_verification_if_eligible(
            db_session, email="rv-past@example.com"
        )

    assert result is True
    email_mock.assert_called_once()


@pytest.mark.asyncio
async def test_resend_verification_updates_timestamp(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "rv-stamp@example.com")
    old_time = datetime.now(UTC) - timedelta(hours=2)
    user.verification_sent_at = old_time
    await db_session.flush()

    with patch("app.services.user_service.EmailService.send_verification_email"):
        await UserService.resend_verification_if_eligible(
            db_session, email="rv-stamp@example.com"
        )

    await db_session.refresh(user)
    assert user.verification_sent_at is not None
    # New timestamp should be more recent than old one
    new_ts = _to_aware_utc(user.verification_sent_at)
    assert new_ts > _to_aware_utc(old_time)


@pytest.mark.asyncio
async def test_resend_verification_rotates_token(db_session: Any) -> None:
    user = await _make_unverified_user(db_session, "rv-rotate@example.com")
    old_time = datetime.now(UTC) - timedelta(hours=2)
    _, old_hash = generate_token()
    user.verification_token = old_hash
    user.verification_sent_at = old_time
    await db_session.flush()

    with patch("app.services.user_service.EmailService.send_verification_email"):
        await UserService.resend_verification_if_eligible(
            db_session, email="rv-rotate@example.com"
        )

    await db_session.refresh(user)
    assert user.verification_token != old_hash


@pytest.mark.asyncio
async def test_resend_verification_naive_sent_at_handled(db_session: Any) -> None:
    """SQLite stores naive datetimes — the cooldown check must not crash."""
    user = await _make_unverified_user(db_session, "rv-naive@example.com")
    # Naive datetime that is definitely 2 hours in the past (outside 5-min cooldown)
    old_naive = (datetime.now(UTC) - timedelta(hours=2)).replace(tzinfo=None)
    user.verification_sent_at = old_naive
    await db_session.flush()

    with patch("app.services.user_service.EmailService.send_verification_email"):
        result = await UserService.resend_verification_if_eligible(
            db_session, email="rv-naive@example.com"
        )

    assert result is True
