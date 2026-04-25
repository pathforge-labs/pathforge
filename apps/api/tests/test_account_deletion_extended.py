"""Extended tests for AccountDeletionService — covers branches missing from test_account_deletion.py.

Focuses on:
- count > 0 branch (str-typed and UUID-typed model loops)
- _delete_by_user_id exception handler
- _cancel_stripe_subscription: no subscription, billing disabled, Stripe error
- _hash_email helper
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User
from app.models.user_activity import UserActivityLog
from app.models.user_profile import UserProfile
from app.services.account_deletion_service import (
    AccountDeletionService,
    _cancel_stripe_subscription,
    _delete_by_user_id,
    _hash_email,
)

# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_verified_user(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("Pass123!"),
        full_name="Test",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ── _hash_email ───────────────────────────────────────────────────────────────


def test_hash_email_returns_16_char_hex() -> None:
    result = _hash_email("test@example.com")
    assert len(result) == 16
    assert all(c in "0123456789abcdef" for c in result)


def test_hash_email_same_input_same_output() -> None:
    assert _hash_email("a@b.com") == _hash_email("a@b.com")


def test_hash_email_different_inputs_differ() -> None:
    assert _hash_email("a@b.com") != _hash_email("c@d.com")


# ── _delete_by_user_id ────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_by_user_id_returns_zero_when_no_rows(db_session: AsyncSession) -> None:
    nonexistent_id = str(uuid.uuid4())
    count = await _delete_by_user_id(db_session, model=UserProfile, user_id=nonexistent_id)
    assert count == 0


@pytest.mark.asyncio
async def test_delete_by_user_id_exception_returns_zero(db_session: AsyncSession) -> None:
    """Exception in execute is caught and returns 0."""
    with patch.object(db_session, "execute", side_effect=Exception("DB failure")):
        count = await _delete_by_user_id(
            db_session, model=UserProfile, user_id="bogus-id"
        )
    assert count == 0


# ── _cancel_stripe_subscription ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_stripe_no_subscription_is_noop(db_session: AsyncSession) -> None:
    user = await _make_verified_user(db_session, "cxs-none@example.com")
    # No subscription — should silently return
    await _cancel_stripe_subscription(db_session, user_id=user.id)  # no error


@pytest.mark.asyncio
async def test_cancel_stripe_billing_disabled_skips(db_session: AsyncSession) -> None:
    from app.core.config import settings
    from app.models.subscription import Subscription

    user = await _make_verified_user(db_session, "cxs-disabled@example.com")
    sub = Subscription(
        user_id=user.id,
        tier="pro",
        status="active",
        stripe_customer_id="cus_x",
        stripe_subscription_id="sub_x",
    )
    db_session.add(sub)
    await db_session.flush()

    with patch.object(settings, "billing_enabled", False):
        mock_stripe = MagicMock()
        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            await _cancel_stripe_subscription(db_session, user_id=user.id)
        mock_stripe.Subscription.cancel.assert_not_called()


@pytest.mark.asyncio
async def test_cancel_stripe_error_is_swallowed(db_session: AsyncSession) -> None:
    """Stripe errors must not bubble up — deletion proceeds regardless."""
    from app.core.config import settings
    from app.models.subscription import Subscription

    user = await _make_verified_user(db_session, "cxs-err@example.com")
    sub = Subscription(
        user_id=user.id,
        tier="pro",
        status="active",
        stripe_customer_id="cus_err",
        stripe_subscription_id="sub_err",
    )
    db_session.add(sub)
    await db_session.flush()

    original = settings.billing_enabled
    object.__setattr__(settings, "billing_enabled", True)
    try:
        mock_stripe = MagicMock()
        mock_stripe.Subscription.cancel.side_effect = Exception("Stripe 500")
        mock_stripe.api_key = None
        with patch.dict("sys.modules", {"stripe": mock_stripe}):
            await _cancel_stripe_subscription(db_session, user_id=user.id)
        # No exception raised — the warning is logged and we continue
    finally:
        object.__setattr__(settings, "billing_enabled", original)


# ── AccountDeletionService.delete_account ─────────────────────────────────────


@pytest.mark.asyncio
async def test_delete_account_with_str_model_records(db_session: AsyncSession) -> None:
    """Count > 0 branch fires when user has UserProfile data."""
    user = await _make_verified_user(db_session, "del-profile@example.com")
    profile = UserProfile(user_id=str(user.id), headline="Engineer")
    db_session.add(profile)
    await db_session.flush()

    result = await AccountDeletionService.delete_account(db_session, user=user)

    assert result["deleted"] is True
    assert result["records_deleted"] >= 1
    assert result["tables_affected"] >= 1
    # UserProfile should appear in the summary
    assert "user_profiles" in result["summary"]


@pytest.mark.asyncio
async def test_delete_account_with_uuid_model_records(db_session: AsyncSession) -> None:
    """Count > 0 branch fires when user has UserActivityLog data."""
    user = await _make_verified_user(db_session, "del-activity@example.com")
    log = UserActivityLog(
        user_id=user.id,
        action="login",
        entity_type="session",
    )
    db_session.add(log)
    await db_session.flush()

    result = await AccountDeletionService.delete_account(db_session, user=user)

    assert result["deleted"] is True
    assert result["records_deleted"] >= 1
    assert "user_activity_logs" in result["summary"]


@pytest.mark.asyncio
async def test_delete_account_returns_correct_totals(db_session: AsyncSession) -> None:
    """records_deleted equals sum of all per-table counts."""
    user = await _make_verified_user(db_session, "del-totals@example.com")

    result = await AccountDeletionService.delete_account(db_session, user=user)

    assert isinstance(result["records_deleted"], int)
    assert isinstance(result["tables_affected"], int)
    assert result["tables_affected"] == len(result["summary"])
    assert result["records_deleted"] == sum(result["summary"].values())
