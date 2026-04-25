"""
PathForge API — Account Deletion Tests
========================================
Sprint 41 Phase 4: Test coverage for DELETE /users/me (GDPR Article 17).

Verifies account deletion, token revocation, Stripe cancellation,
unauthenticated rejection, and post-deletion token invalidation.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password
from app.models.user import User

# ── Helpers ──────────────────────────────────────────────────────


async def _create_user_with_token(
    db_session: AsyncSession,
    client: AsyncClient,
    email: str = "delete-me@pathforge.eu",
) -> tuple[User, str, dict[str, str]]:
    """Create a user directly in DB and return (user, access_token, headers)."""
    user = User(
        email=email,
        hashed_password=hash_password("DeleteMe123!"),
        full_name="Delete Me",
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)

    token = create_access_token(str(user.id))
    headers = {"Authorization": f"Bearer {token}"}
    return user, token, headers


# ══════════════════════════════════════════════════════════════════
# ACCOUNT DELETION (DELETE /users/me)
# ══════════════════════════════════════════════════════════════════


class TestAccountDeletion:
    """Tests for DELETE /api/v1/users/me — GDPR Article 17."""

    DELETE_ENDPOINT = "/api/v1/users/me"

    @pytest.mark.asyncio
    async def test_delete_account_success(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        """Authenticated user can delete their account; returns deletion summary."""
        _user, _, headers = await _create_user_with_token(
            db_session, client, email="del-success@pathforge.eu",
        )

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ):
            response = await client.delete(
                self.DELETE_ENDPOINT, headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["deleted"] is True
        assert "records_deleted" in body
        assert "tables_affected" in body
        assert isinstance(body["records_deleted"], int)
        assert isinstance(body["tables_affected"], int)

    @pytest.mark.asyncio
    async def test_delete_account_token_revocation(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        """Account deletion blacklists the current access token."""
        _user, _, headers = await _create_user_with_token(
            db_session, client, email="del-revoke@pathforge.eu",
        )

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            response = await client.delete(
                self.DELETE_ENDPOINT, headers=headers,
            )

        assert response.status_code == 200
        mock_revoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_account_stripe_cancellation(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        """Account deletion cancels active Stripe subscription."""
        from app.core.config import settings
        from app.models.subscription import Subscription

        user, _, headers = await _create_user_with_token(
            db_session, client, email="del-stripe@pathforge.eu",
        )

        # Create a subscription for this user
        subscription = Subscription(
            user_id=user.id,
            tier="pro",
            status="active",
            stripe_customer_id="cus_test_del",
            stripe_subscription_id="sub_test_del",
        )
        db_session.add(subscription)
        await db_session.flush()

        # Enable billing and mock Stripe
        original_billing = settings.billing_enabled
        object.__setattr__(settings, "billing_enabled", True)

        mock_stripe_sub = MagicMock()
        mock_stripe_module = MagicMock()
        mock_stripe_module.Subscription.cancel = mock_stripe_sub

        with (
            patch(
                "app.core.token_blacklist.TokenBlacklist.revoke",
                new_callable=AsyncMock,
            ),
            patch.dict("sys.modules", {"stripe": mock_stripe_module}),
        ):
            response = await client.delete(
                self.DELETE_ENDPOINT, headers=headers,
            )

        object.__setattr__(settings, "billing_enabled", original_billing)

        assert response.status_code == 200
        mock_stripe_sub.assert_called_once_with("sub_test_del")

    @pytest.mark.asyncio
    async def test_delete_account_unauthenticated(
        self, client: AsyncClient,
    ) -> None:
        """DELETE /users/me without auth token returns 401."""
        response = await client.delete(self.DELETE_ENDPOINT)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_account_user_gone_after(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        """After deletion, the user record no longer exists in the database."""
        user, _, headers = await _create_user_with_token(
            db_session, client, email="del-gone@pathforge.eu",
        )
        user_id = user.id

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ):
            response = await client.delete(
                self.DELETE_ENDPOINT, headers=headers,
            )

        assert response.status_code == 200

        # Verify user is gone from database
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        assert result.scalar_one_or_none() is None
