"""
PathForge — Auth Routes Extra Coverage
========================================
Targeted tests filling coverage gaps in app/api/v1/auth.py for:

- forgot_password active-user happy path (token gen + email send)
- reset_password success + PasswordResetError → 400
- verify_email success (welcome email + clear token)
- verify_email invalid token (no matching user) → 400
- verify_email expired token → 400
- resend_verification orchestration
- login error branches (Invalid / Inactive / Unverified / OAuth-only)
- refresh_token success (user lookup + new tokens)
- logout PyJWTError branch (already-invalid bearer)
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
)
from app.main import app
from app.models.user import User
from app.services.user_service_errors import (
    InactiveAccountError,
    InvalidCredentialsError,
    InvalidResetTokenError,
    OAuthOnlyAccountError,
    UnverifiedAccountError,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_user(
    db: AsyncSession,
    email: str,
    *,
    is_verified: bool = True,
    is_active: bool = True,
    verification_token_hash: str | None = None,
    verification_sent_at: datetime | None = None,
    password_reset_token_hash: str | None = None,
    password_reset_sent_at: datetime | None = None,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name="Test",
        is_active=is_active,
        is_verified=is_verified,
        verification_token=verification_token_hash,
        verification_sent_at=verification_sent_at,
        password_reset_token=password_reset_token_hash,
        password_reset_sent_at=password_reset_sent_at,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ═══════════════════════════════════════════════════════════════════════════════
# forgot_password
# ═══════════════════════════════════════════════════════════════════════════════


class TestForgotPassword:
    """POST /auth/forgot-password — covers lines 272-286."""

    async def test_forgot_password_active_user_sends_email(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Active user → token generated, email sent, 200 response."""
        await _make_user(db_session, "fp-active@example.com")
        await db_session.commit()

        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_password_reset_email", new=email_mock
        ):
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "fp-active@example.com"},
            )

        assert resp.status_code == 200
        email_mock.assert_called_once()
        assert email_mock.call_args.kwargs["to"] == "fp-active@example.com"
        # raw token should be a non-trivial string
        assert len(email_mock.call_args.kwargs["token"]) > 10

    async def test_forgot_password_unknown_email_still_returns_200(
        self, client: AsyncClient
    ) -> None:
        """Anti-enumeration: unknown email also returns 200 with same body."""
        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_password_reset_email", new=email_mock
        ):
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "fp-unknown@example.com"},
            )

        assert resp.status_code == 200
        email_mock.assert_not_called()

    async def test_forgot_password_inactive_user_skips_email(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Inactive user → no email sent (but still 200 to prevent leak)."""
        await _make_user(db_session, "fp-inactive@example.com", is_active=False)
        await db_session.commit()

        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_password_reset_email", new=email_mock
        ):
            resp = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "fp-inactive@example.com"},
            )

        assert resp.status_code == 200
        email_mock.assert_not_called()


# ═══════════════════════════════════════════════════════════════════════════════
# reset_password
# ═══════════════════════════════════════════════════════════════════════════════


class TestResetPassword:
    """POST /auth/reset-password — covers lines 313-320."""

    async def test_reset_password_success_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        with patch(
            "app.api.v1.auth.UserService.reset_password_with_token",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.post(
                "/api/v1/auth/reset-password",
                json={"token": "any-token", "new_password": "NewPass456!"},
            )

        assert resp.status_code == 200
        assert "successfully" in resp.json()["message"].lower()

    async def test_reset_password_invalid_token_returns_400(
        self, client: AsyncClient
    ) -> None:
        with patch(
            "app.api.v1.auth.UserService.reset_password_with_token",
            new_callable=AsyncMock,
            side_effect=InvalidResetTokenError(),
        ):
            resp = await client.post(
                "/api/v1/auth/reset-password",
                json={"token": "bad-token", "new_password": "NewPass456!"},
            )

        assert resp.status_code == 400


# ═══════════════════════════════════════════════════════════════════════════════
# verify_email
# ═══════════════════════════════════════════════════════════════════════════════


class TestVerifyEmail:
    """POST /auth/verify-email — covers lines 343-374."""

    async def test_verify_email_success_marks_user_verified(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        raw_token = "verify-raw-token-123"
        hashed = hashlib.sha256(raw_token.encode()).hexdigest()
        user = await _make_user(
            db_session,
            "ve-success@example.com",
            is_verified=False,
            verification_token_hash=hashed,
            verification_sent_at=datetime.now(UTC),
        )
        await db_session.commit()

        welcome_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_welcome_email", new=welcome_mock
        ):
            resp = await client.post(
                "/api/v1/auth/verify-email", json={"token": raw_token}
            )

        assert resp.status_code == 200
        assert "verified" in resp.json()["message"].lower()
        welcome_mock.assert_called_once_with(
            to=user.email, name=user.full_name
        )

        await db_session.refresh(user)
        assert user.is_verified is True
        assert user.verification_token is None
        assert user.verification_sent_at is None

    async def test_verify_email_unknown_token_returns_400(
        self, client: AsyncClient
    ) -> None:
        resp = await client.post(
            "/api/v1/auth/verify-email", json={"token": "no-match-token"}
        )
        assert resp.status_code == 400
        assert "invalid" in resp.json()["detail"].lower()

    async def test_verify_email_expired_token_returns_400(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        raw_token = "expired-token-xyz"
        hashed = hashlib.sha256(raw_token.encode()).hexdigest()
        # send_at is far in the past so any reasonable expiry window is exceeded
        user = await _make_user(
            db_session,
            "ve-expired@example.com",
            is_verified=False,
            verification_token_hash=hashed,
            verification_sent_at=datetime.now(UTC) - timedelta(days=30),
        )
        await db_session.commit()

        resp = await client.post(
            "/api/v1/auth/verify-email", json={"token": raw_token}
        )

        assert resp.status_code == 400
        assert "expired" in resp.json()["detail"].lower()

        # Token should be cleared on expiry
        await db_session.refresh(user)
        assert user.verification_token is None
        assert user.verification_sent_at is None
        assert user.is_verified is False  # still unverified


# ═══════════════════════════════════════════════════════════════════════════════
# resend_verification
# ═══════════════════════════════════════════════════════════════════════════════


class TestResendVerification:
    """POST /auth/resend-verification — covers line 397-398."""

    async def test_resend_verification_returns_200(self, client: AsyncClient) -> None:
        with patch(
            "app.api.v1.auth.UserService.resend_verification_if_eligible",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client.post(
                "/api/v1/auth/resend-verification",
                json={"email": "rv-anon@example.com"},
            )

        assert resp.status_code == 200
        assert "verification" in resp.json()["message"].lower()


# ═══════════════════════════════════════════════════════════════════════════════
# login error branches
# ═══════════════════════════════════════════════════════════════════════════════


class TestLoginErrorBranches:
    """POST /auth/login — covers lines 114-132 (exception handlers)."""

    async def test_login_invalid_credentials_returns_401(
        self, client: AsyncClient
    ) -> None:
        with patch(
            "app.api.v1.auth.UserService.authenticate",
            new_callable=AsyncMock,
            side_effect=InvalidCredentialsError(),
        ):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "a@b.com", "password": "WrongPass1!"},
            )
        assert resp.status_code == 401

    async def test_login_inactive_account_returns_403(
        self, client: AsyncClient
    ) -> None:
        with patch(
            "app.api.v1.auth.UserService.authenticate",
            new_callable=AsyncMock,
            side_effect=InactiveAccountError(),
        ):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "a@b.com", "password": "Pass1234!"},
            )
        assert resp.status_code == 403

    async def test_login_unverified_account_returns_403(
        self, client: AsyncClient
    ) -> None:
        with patch(
            "app.api.v1.auth.UserService.authenticate",
            new_callable=AsyncMock,
            side_effect=UnverifiedAccountError(),
        ):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "a@b.com", "password": "Pass1234!"},
            )
        assert resp.status_code == 403

    async def test_login_oauth_only_returns_403(
        self, client: AsyncClient
    ) -> None:
        with patch(
            "app.api.v1.auth.UserService.authenticate",
            new_callable=AsyncMock,
            side_effect=OAuthOnlyAccountError(provider="google"),
        ):
            resp = await client.post(
                "/api/v1/auth/login",
                json={"email": "a@b.com", "password": "Pass1234!"},
            )
        assert resp.status_code == 403


# ═══════════════════════════════════════════════════════════════════════════════
# refresh_token success
# ═══════════════════════════════════════════════════════════════════════════════


class TestRefreshSuccess:
    """POST /auth/refresh — covers lines 197-208 (success response)."""

    async def test_refresh_success_returns_new_tokens(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "rf-ok@example.com")
        await db_session.commit()
        refresh = create_refresh_token(str(user.id))

        resp = await client.post(
            "/api/v1/auth/refresh", json={"refresh_token": refresh}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"


# ═══════════════════════════════════════════════════════════════════════════════
# logout PyJWTError branch
# ═══════════════════════════════════════════════════════════════════════════════


class TestLogoutInvalidAccessToken:
    """POST /auth/logout — covers line 235-236 (PyJWTError swallowed)."""

    async def test_logout_with_garbage_bearer_swallows_jwterror(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Path: oauth2_scheme returns the bearer; the second jwt.decode
        in the logout handler receives a non-JWT string, raises PyJWTError,
        and we hit the ``except PyJWTError: pass`` branch on line 235-236.
        We override ``get_current_user`` to bypass auth so the bad token
        reaches the logout body itself.

        Override note: ``app.core.auth.get_current_user`` is a direct
        re-export of ``app.core.security.get_current_user`` (both
        resolve to the same callable object), so a single override
        covers both import paths — overriding twice was redundant
        (Gemini PR #21 review).
        """
        user = await _make_user(db_session, "lo-jwt@example.com")
        await db_session.commit()

        async def _override_user() -> User:
            return user

        app.dependency_overrides[get_current_user] = _override_user
        try:
            with patch(
                "app.api.v1.auth.token_blacklist.revoke",
                new_callable=AsyncMock,
            ):
                resp = await client.post(
                    "/api/v1/auth/logout",
                    headers={"Authorization": "Bearer not-a-real-jwt-token"},
                )
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_user, None)

    async def test_logout_with_invalid_refresh_token_still_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Path: refresh_token branch — non-JWT in body is swallowed by the
        ``except (PyJWTError, ConnectionError, OSError): pass`` block."""
        user = await _make_user(db_session, "lo-rjwt@example.com")
        await db_session.commit()

        async def _override_user() -> User:
            return user

        app.dependency_overrides[get_current_user] = _override_user
        try:
            access = create_access_token(str(user.id))
            with patch(
                "app.api.v1.auth.token_blacklist.revoke",
                new_callable=AsyncMock,
            ):
                resp = await client.post(
                    "/api/v1/auth/logout",
                    headers={"Authorization": f"Bearer {access}"},
                    json={"refresh_token": "not-a-real-jwt"},
                )
            assert resp.status_code == 204
        finally:
            app.dependency_overrides.pop(get_current_user, None)
