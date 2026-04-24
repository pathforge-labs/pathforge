"""
PathForge API — Comprehensive Auth Route Tests
==================================================
Integration tests for every endpoint exposed by
``app.api.v1.auth``. These tests hit the real FastAPI
app through the ``client`` fixture and validate HTTP
behaviour, DB side-effects, and external collaborator
interaction (email service, Turnstile, token blacklist).
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_refresh_token,
    hash_password,
)
from app.models.user import User
from app.services.email_service import generate_token

if TYPE_CHECKING:
    pass

pytestmark = pytest.mark.asyncio


# ── Constants ────────────────────────────────────────────────────

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
REFRESH_URL = "/api/v1/auth/refresh"
LOGOUT_URL = "/api/v1/auth/logout"
FORGOT_URL = "/api/v1/auth/forgot-password"
RESET_URL = "/api/v1/auth/reset-password"
VERIFY_URL = "/api/v1/auth/verify-email"
RESEND_URL = "/api/v1/auth/resend-verification"

VALID_PASSWORD = "RouteTest123!"
NEW_PASSWORD = "RouteTestNew456!"


# ── Shared Helpers ───────────────────────────────────────────────


async def _register(
    client: AsyncClient,
    *,
    email: str,
    password: str = VALID_PASSWORD,
    full_name: str = "Route Test",
) -> dict[str, str]:
    """Register a user via the public endpoint and return {..., password}."""
    response = await client.post(
        REGISTER_URL,
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert response.status_code == 201
    return {**response.json(), "password": password}


async def _login(
    client: AsyncClient, email: str, password: str = VALID_PASSWORD,
) -> dict[str, str]:
    response = await client.post(
        LOGIN_URL, json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


async def _fetch_user(db_session: AsyncSession, email: str) -> User:
    result = await db_session.execute(select(User).where(User.email == email))
    return result.scalar_one()


def _build_refresh_token(
    subject: str, *, secret: str | None = None, expires_delta: timedelta | None = None,
    include_type: bool = True, include_sub: bool = True,
) -> str:
    """Build a refresh token directly for fine-grained refresh tests."""
    now = datetime.now(UTC)
    payload: dict[str, object] = {
        "iat": now,
        "exp": now + (expires_delta or timedelta(days=7)),
        "jti": str(_uuid.uuid4()),
    }
    if include_sub:
        payload["sub"] = subject
    if include_type:
        payload["type"] = "refresh"
    return jwt.encode(
        payload,
        secret or settings.jwt_refresh_secret,
        algorithm=settings.jwt_algorithm,
    )


# ═════════════════════════════════════════════════════════════════
# REGISTER
# ═════════════════════════════════════════════════════════════════


class TestRegister:
    """POST /api/v1/auth/register."""

    async def test_register_success_returns_201(self, client: AsyncClient) -> None:
        with (
            patch(
                "app.core.turnstile.verify_turnstile_token",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.auth.EmailService.send_verification_email",
                new=MagicMock(return_value=True),
            ),
        ):
            response = await client.post(
                REGISTER_URL,
                json={
                    "email": "reg-ok@pathforge.eu",
                    "password": VALID_PASSWORD,
                    "full_name": "Reg OK",
                },
            )

        assert response.status_code == 201
        body = response.json()
        assert body["email"] == "reg-ok@pathforge.eu"
        assert body["is_active"] is True
        assert body["is_verified"] is False
        assert "id" in body

    async def test_register_calls_turnstile_verification(
        self, client: AsyncClient,
    ) -> None:
        turnstile_mock = AsyncMock(return_value=True)
        with (
            patch("app.core.turnstile.verify_turnstile_token", new=turnstile_mock),
            patch(
                "app.api.v1.auth.EmailService.send_verification_email",
                new=MagicMock(return_value=True),
            ),
        ):
            response = await client.post(
                REGISTER_URL,
                json={
                    "email": "reg-turnstile@pathforge.eu",
                    "password": VALID_PASSWORD,
                    "full_name": "Turnstile",
                    "turnstile_token": "ts-xyz",
                },
            )

        assert response.status_code == 201
        turnstile_mock.assert_awaited_once_with("ts-xyz")

    async def test_register_sends_verification_email_with_token(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        email_mock = MagicMock(return_value=True)
        with (
            patch(
                "app.core.turnstile.verify_turnstile_token",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.auth.EmailService.send_verification_email",
                new=email_mock,
            ),
        ):
            await client.post(
                REGISTER_URL,
                json={
                    "email": "reg-email@pathforge.eu",
                    "password": VALID_PASSWORD,
                    "full_name": "Email Emitter",
                },
            )

        email_mock.assert_called_once()
        call_kwargs = email_mock.call_args.kwargs
        assert call_kwargs["to"] == "reg-email@pathforge.eu"
        assert call_kwargs["name"] == "Email Emitter"
        assert isinstance(call_kwargs["token"], str)
        assert len(call_kwargs["token"]) > 10

    async def test_register_sets_verification_token_hash_in_db(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        with (
            patch(
                "app.core.turnstile.verify_turnstile_token",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.auth.EmailService.send_verification_email",
                new=MagicMock(return_value=True),
            ),
        ):
            await client.post(
                REGISTER_URL,
                json={
                    "email": "reg-hash@pathforge.eu",
                    "password": VALID_PASSWORD,
                    "full_name": "Hash",
                },
            )

        user = await _fetch_user(db_session, "reg-hash@pathforge.eu")
        assert user.verification_token is not None
        assert user.verification_sent_at is not None

    async def test_register_duplicate_email_returns_409(
        self, client: AsyncClient,
    ) -> None:
        with (
            patch(
                "app.core.turnstile.verify_turnstile_token",
                new_callable=AsyncMock,
                return_value=True,
            ),
            patch(
                "app.api.v1.auth.EmailService.send_verification_email",
                new=MagicMock(return_value=True),
            ),
        ):
            first = await client.post(
                REGISTER_URL,
                json={
                    "email": "reg-dup@pathforge.eu",
                    "password": VALID_PASSWORD,
                    "full_name": "Original",
                },
            )
            assert first.status_code == 201

            second = await client.post(
                REGISTER_URL,
                json={
                    "email": "reg-dup@pathforge.eu",
                    "password": "AnotherPass789!",
                    "full_name": "Copy",
                },
            )

        assert second.status_code == 409
        assert "already exists" in second.json()["detail"].lower()

    async def test_register_rejects_weak_password(self, client: AsyncClient) -> None:
        response = await client.post(
            REGISTER_URL,
            json={
                "email": "reg-weak@pathforge.eu",
                "password": "alllowercase",
                "full_name": "Weak",
            },
        )
        assert response.status_code == 422


# ═════════════════════════════════════════════════════════════════
# LOGIN
# ═════════════════════════════════════════════════════════════════


class TestLogin:
    """POST /api/v1/auth/login."""

    async def test_login_success_returns_tokens(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="login-ok@pathforge.eu")
        response = await client.post(
            LOGIN_URL,
            json={"email": user["email"], "password": user["password"]},
        )
        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert "refresh_token" in body
        assert body["token_type"] == "bearer"

    async def test_login_access_token_decodes_with_access_secret(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="login-access@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        decoded = jwt.decode(
            tokens["access_token"],
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        assert decoded["type"] == "access"
        assert decoded["sub"]

    async def test_login_refresh_token_decodes_with_refresh_secret(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="login-refresh@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        decoded = jwt.decode(
            tokens["refresh_token"],
            settings.jwt_refresh_secret,
            algorithms=[settings.jwt_algorithm],
        )
        assert decoded["type"] == "refresh"

    async def test_login_wrong_password_returns_401(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="login-badpass@pathforge.eu")
        response = await client.post(
            LOGIN_URL,
            json={"email": user["email"], "password": "TotallyWrong!1"},
        )
        assert response.status_code == 401
        assert "incorrect" in response.json()["detail"].lower()

    async def test_login_unknown_email_returns_401(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            LOGIN_URL,
            json={"email": "nobody@pathforge.eu", "password": VALID_PASSWORD},
        )
        assert response.status_code == 401

    async def test_login_inactive_user_returns_403(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        user = User(
            email="login-inactive@pathforge.eu",
            hashed_password=hash_password(VALID_PASSWORD),
            full_name="Inactive",
            is_active=False,
            is_verified=True,
        )
        db_session.add(user)
        await db_session.flush()

        response = await client.post(
            LOGIN_URL,
            json={"email": user.email, "password": VALID_PASSWORD},
        )
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    async def test_login_invalid_email_format_returns_422(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            LOGIN_URL,
            json={"email": "not-an-email", "password": VALID_PASSWORD},
        )
        assert response.status_code == 422

    @pytest.mark.no_auto_verify
    async def test_login_unverified_user_returns_403(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        """F28 audit guardrail: unverified accounts must be rejected at /login.

        Registers a fresh user and hits /login with the correct password
        but without verifying the account. Expects 403 + a message that
        points the user at the verification flow. Uses
        ``@pytest.mark.no_auto_verify`` to disable the conftest shortcut
        that normally flips ``is_verified`` before authentication.
        """
        user = User(
            email="login-unverified@pathforge.eu",
            hashed_password=hash_password(VALID_PASSWORD),
            full_name="Unverified",
            is_active=True,
            is_verified=False,
        )
        db_session.add(user)
        await db_session.flush()

        response = await client.post(
            LOGIN_URL,
            json={"email": user.email, "password": VALID_PASSWORD},
        )
        assert response.status_code == 403
        assert "verify your email" in response.json()["detail"].lower()


# ═════════════════════════════════════════════════════════════════
# REFRESH
# ═════════════════════════════════════════════════════════════════


class TestRefresh:
    """POST /api/v1/auth/refresh."""

    async def test_refresh_success_returns_new_tokens(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="ref-ok@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        with patch(
            "app.api.v1.auth.token_blacklist.consume_once",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = await client.post(
                REFRESH_URL,
                json={"refresh_token": tokens["refresh_token"]},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["access_token"] != tokens["access_token"]
        assert body["refresh_token"] != tokens["refresh_token"]

    async def test_refresh_expired_token_returns_401(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        user = await _register(client, email="ref-expired@pathforge.eu")
        db_user = await _fetch_user(db_session, user["email"])
        expired = _build_refresh_token(
            str(db_user.id), expires_delta=timedelta(seconds=-5),
        )

        response = await client.post(
            REFRESH_URL, json={"refresh_token": expired},
        )
        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower() or "expired" in response.json()["detail"].lower()

    async def test_refresh_access_token_type_rejected(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="ref-wrong-type@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        response = await client.post(
            REFRESH_URL, json={"refresh_token": tokens["access_token"]},
        )
        assert response.status_code == 401

    async def test_refresh_token_missing_sub_returns_401(
        self, client: AsyncClient,
    ) -> None:
        token = _build_refresh_token("unused", include_sub=False)
        response = await client.post(
            REFRESH_URL, json={"refresh_token": token},
        )
        assert response.status_code == 401

    async def test_refresh_token_missing_type_returns_401(
        self, client: AsyncClient,
    ) -> None:
        token = _build_refresh_token(str(_uuid.uuid4()), include_type=False)
        response = await client.post(
            REFRESH_URL, json={"refresh_token": token},
        )
        assert response.status_code == 401

    async def test_refresh_malformed_token_returns_401(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            REFRESH_URL, json={"refresh_token": "not.a.token"},
        )
        assert response.status_code == 401

    async def test_refresh_wrong_secret_returns_401(
        self, client: AsyncClient,
    ) -> None:
        token = _build_refresh_token(
            str(_uuid.uuid4()), secret="different-wrong-secret-32-bytes!!",
        )
        response = await client.post(
            REFRESH_URL, json={"refresh_token": token},
        )
        assert response.status_code == 401

    async def test_refresh_replay_detected_returns_401(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="ref-replay@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        with patch(
            "app.api.v1.auth.token_blacklist.consume_once",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = await client.post(
                REFRESH_URL,
                json={"refresh_token": tokens["refresh_token"]},
            )

        assert response.status_code == 401
        assert "already been used" in response.json()["detail"].lower()

    async def test_refresh_user_not_found_returns_401(
        self, client: AsyncClient,
    ) -> None:
        token = create_refresh_token(str(_uuid.uuid4()))
        with patch(
            "app.api.v1.auth.token_blacklist.consume_once",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = await client.post(
                REFRESH_URL, json={"refresh_token": token},
            )
        assert response.status_code == 401
        assert "not found" in response.json()["detail"].lower() or "inactive" in response.json()["detail"].lower()

    async def test_refresh_inactive_user_returns_401(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        user = await _register(client, email="ref-inactive@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        db_user = await _fetch_user(db_session, user["email"])
        db_user.is_active = False
        await db_session.flush()

        with patch(
            "app.api.v1.auth.token_blacklist.consume_once",
            new_callable=AsyncMock,
            return_value=True,
        ):
            response = await client.post(
                REFRESH_URL,
                json={"refresh_token": tokens["refresh_token"]},
            )
        assert response.status_code == 401

    async def test_refresh_fail_open_on_blacklist_error(
        self, client: AsyncClient,
    ) -> None:
        """In fail-open mode, refresh still succeeds when blacklist raises."""
        user = await _register(client, email="ref-failopen@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        with patch(
            "app.api.v1.auth.token_blacklist.consume_once",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis offline"),
        ):
            response = await client.post(
                REFRESH_URL,
                json={"refresh_token": tokens["refresh_token"]},
            )

        assert response.status_code == 200
        assert "access_token" in response.json()

    async def test_refresh_fail_closed_returns_503(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When fail-closed, refresh returns 503 if blacklist backend errors."""
        monkeypatch.setattr(settings, "token_blacklist_fail_mode", "closed")
        user = await _register(client, email="ref-failclosed@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        with patch(
            "app.api.v1.auth.token_blacklist.consume_once",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis offline"),
        ):
            response = await client.post(
                REFRESH_URL,
                json={"refresh_token": tokens["refresh_token"]},
            )

        # Restore fail-open for any following tests
        monkeypatch.setattr(settings, "token_blacklist_fail_mode", "open")
        assert response.status_code == 503


# ═════════════════════════════════════════════════════════════════
# LOGOUT
# ═════════════════════════════════════════════════════════════════


class TestLogout:
    """POST /api/v1/auth/logout."""

    async def test_logout_success_returns_204(self, client: AsyncClient) -> None:
        user = await _register(client, email="logout-ok@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            response = await client.post(
                LOGOUT_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

        assert response.status_code == 204
        mock_revoke.assert_called_once()

    async def test_logout_requires_authentication(self, client: AsyncClient) -> None:
        response = await client.post(LOGOUT_URL)
        assert response.status_code == 401

    async def test_logout_invalid_bearer_returns_401(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            LOGOUT_URL, headers={"Authorization": "Bearer not.a.jwt"},
        )
        assert response.status_code == 401

    async def test_logout_revokes_correct_access_jti(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="logout-jti@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        decoded = jwt.decode(
            tokens["access_token"],
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
        expected_jti = decoded["jti"]

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            await client.post(
                LOGOUT_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

        args, kwargs = mock_revoke.call_args
        assert args[0] == expected_jti
        assert kwargs["ttl_seconds"] > 0

    async def test_logout_revokes_refresh_when_provided(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="logout-ref@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            response = await client.post(
                LOGOUT_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
                json={"refresh_token": tokens["refresh_token"]},
            )

        assert response.status_code == 204
        assert mock_revoke.call_count == 2

    async def test_logout_without_refresh_only_revokes_access(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="logout-accessonly@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            response = await client.post(
                LOGOUT_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

        assert response.status_code == 204
        assert mock_revoke.call_count == 1

    async def test_logout_invalid_refresh_token_still_succeeds(
        self, client: AsyncClient,
    ) -> None:
        user = await _register(client, email="logout-badref@pathforge.eu")
        tokens = await _login(client, user["email"], user["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ):
            response = await client.post(
                LOGOUT_URL,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
                json={"refresh_token": "junk.refresh.token"},
            )

        assert response.status_code == 204


# ═════════════════════════════════════════════════════════════════
# FORGOT PASSWORD
# ═════════════════════════════════════════════════════════════════


class TestForgotPassword:
    """POST /api/v1/auth/forgot-password."""

    async def test_forgot_password_existing_user_returns_200(
        self, client: AsyncClient,
    ) -> None:
        await _register(client, email="fp-ok@pathforge.eu")
        with patch(
            "app.api.v1.auth.EmailService.send_password_reset_email",
            new=MagicMock(return_value=True),
        ):
            response = await client.post(
                FORGOT_URL, json={"email": "fp-ok@pathforge.eu"},
            )

        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()

    async def test_forgot_password_sends_email_for_active_user(
        self, client: AsyncClient,
    ) -> None:
        await _register(client, email="fp-sends@pathforge.eu")
        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_password_reset_email",
            new=email_mock,
        ):
            await client.post(FORGOT_URL, json={"email": "fp-sends@pathforge.eu"})

        email_mock.assert_called_once()
        kwargs = email_mock.call_args.kwargs
        assert kwargs["to"] == "fp-sends@pathforge.eu"
        assert isinstance(kwargs["token"], str)

    async def test_forgot_password_stores_hashed_token(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="fp-hash@pathforge.eu")
        with patch(
            "app.api.v1.auth.EmailService.send_password_reset_email",
            new=MagicMock(return_value=True),
        ):
            await client.post(FORGOT_URL, json={"email": "fp-hash@pathforge.eu"})

        user = await _fetch_user(db_session, "fp-hash@pathforge.eu")
        assert user.password_reset_token is not None
        assert user.password_reset_sent_at is not None

    async def test_forgot_password_unknown_email_returns_200(
        self, client: AsyncClient,
    ) -> None:
        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_password_reset_email",
            new=email_mock,
        ):
            response = await client.post(
                FORGOT_URL, json={"email": "ghost-user@pathforge.eu"},
            )

        assert response.status_code == 200
        email_mock.assert_not_called()

    async def test_forgot_password_inactive_user_no_email(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        inactive = User(
            email="fp-inactive@pathforge.eu",
            hashed_password=hash_password(VALID_PASSWORD),
            full_name="Inactive",
            is_active=False,
        )
        db_session.add(inactive)
        await db_session.flush()

        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_password_reset_email",
            new=email_mock,
        ):
            response = await client.post(
                FORGOT_URL, json={"email": inactive.email},
            )

        assert response.status_code == 200
        email_mock.assert_not_called()

    async def test_forgot_password_invalid_email_returns_422(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(FORGOT_URL, json={"email": "notanemail"})
        assert response.status_code == 422


# ═════════════════════════════════════════════════════════════════
# RESET PASSWORD
# ═════════════════════════════════════════════════════════════════


class TestResetPassword:
    """POST /api/v1/auth/reset-password."""

    async def test_reset_password_success(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(
            client, email="rp-ok@pathforge.eu", password="InitialPass123!",
        )
        user = await _fetch_user(db_session, "rp-ok@pathforge.eu")
        raw, hashed = generate_token()
        user.password_reset_token = hashed
        user.password_reset_sent_at = datetime.now(UTC)
        await db_session.flush()

        response = await client.post(
            RESET_URL,
            json={"token": raw, "new_password": NEW_PASSWORD},
        )

        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()

    async def test_reset_password_invalid_token_returns_400(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            RESET_URL,
            json={"token": "not-a-real-token", "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    async def test_reset_password_expired_token_returns_400(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="rp-exp@pathforge.eu")
        user = await _fetch_user(db_session, "rp-exp@pathforge.eu")
        raw, hashed = generate_token()
        user.password_reset_token = hashed
        user.password_reset_sent_at = datetime.now(UTC) - timedelta(hours=2)
        await db_session.flush()

        response = await client.post(
            RESET_URL, json={"token": raw, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    async def test_reset_password_clears_token(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="rp-clear@pathforge.eu")
        user = await _fetch_user(db_session, "rp-clear@pathforge.eu")
        raw, hashed = generate_token()
        user.password_reset_token = hashed
        user.password_reset_sent_at = datetime.now(UTC)
        await db_session.flush()

        await client.post(
            RESET_URL, json={"token": raw, "new_password": NEW_PASSWORD},
        )

        await db_session.refresh(user)
        assert user.password_reset_token is None
        assert user.password_reset_sent_at is None

    async def test_reset_password_sets_tokens_invalidated_at(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="rp-invalidated@pathforge.eu")
        user = await _fetch_user(db_session, "rp-invalidated@pathforge.eu")
        assert user.tokens_invalidated_at is None

        raw, hashed = generate_token()
        user.password_reset_token = hashed
        user.password_reset_sent_at = datetime.now(UTC)
        await db_session.flush()

        await client.post(
            RESET_URL, json={"token": raw, "new_password": NEW_PASSWORD},
        )

        await db_session.refresh(user)
        assert user.tokens_invalidated_at is not None

    async def test_reset_password_actually_changes_password(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(
            client, email="rp-changes@pathforge.eu", password="OldOne123!",
        )
        user = await _fetch_user(db_session, "rp-changes@pathforge.eu")
        raw, hashed = generate_token()
        user.password_reset_token = hashed
        user.password_reset_sent_at = datetime.now(UTC)
        await db_session.flush()

        await client.post(
            RESET_URL, json={"token": raw, "new_password": "BrandNewPw456!"},
        )

        login = await client.post(
            LOGIN_URL,
            json={
                "email": "rp-changes@pathforge.eu",
                "password": "BrandNewPw456!",
            },
        )
        assert login.status_code == 200

    async def test_reset_password_missing_timestamp_returns_400(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        """If password_reset_sent_at is None, reset is rejected."""
        await _register(client, email="rp-nots@pathforge.eu")
        user = await _fetch_user(db_session, "rp-nots@pathforge.eu")
        raw, hashed = generate_token()
        user.password_reset_token = hashed
        user.password_reset_sent_at = None
        await db_session.flush()

        response = await client.post(
            RESET_URL, json={"token": raw, "new_password": NEW_PASSWORD},
        )
        assert response.status_code == 400

    async def test_reset_password_weak_password_returns_422(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            RESET_URL,
            json={"token": "any", "new_password": "weakpass"},
        )
        assert response.status_code == 422


# ═════════════════════════════════════════════════════════════════
# VERIFY EMAIL
# ═════════════════════════════════════════════════════════════════


class TestVerifyEmail:
    """POST /api/v1/auth/verify-email."""

    async def test_verify_email_success(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="ve-ok@pathforge.eu")
        user = await _fetch_user(db_session, "ve-ok@pathforge.eu")
        raw, hashed = generate_token()
        user.verification_token = hashed
        user.verification_sent_at = datetime.now(UTC)
        await db_session.flush()

        with patch(
            "app.api.v1.auth.EmailService.send_welcome_email",
            new=MagicMock(return_value=True),
        ):
            response = await client.post(VERIFY_URL, json={"token": raw})

        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

    async def test_verify_email_marks_user_verified(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="ve-mark@pathforge.eu")
        user = await _fetch_user(db_session, "ve-mark@pathforge.eu")
        assert user.is_verified is False

        raw, hashed = generate_token()
        user.verification_token = hashed
        user.verification_sent_at = datetime.now(UTC)
        await db_session.flush()

        with patch(
            "app.api.v1.auth.EmailService.send_welcome_email",
            new=MagicMock(return_value=True),
        ):
            await client.post(VERIFY_URL, json={"token": raw})

        await db_session.refresh(user)
        assert user.is_verified is True
        assert user.verification_token is None
        assert user.verification_sent_at is None

    async def test_verify_email_sends_welcome_email(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(
            client, email="ve-welcome@pathforge.eu", full_name="Welcome User",
        )
        user = await _fetch_user(db_session, "ve-welcome@pathforge.eu")
        raw, hashed = generate_token()
        user.verification_token = hashed
        user.verification_sent_at = datetime.now(UTC)
        await db_session.flush()

        welcome_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_welcome_email", new=welcome_mock,
        ):
            response = await client.post(VERIFY_URL, json={"token": raw})

        assert response.status_code == 200
        welcome_mock.assert_called_once()
        kwargs = welcome_mock.call_args.kwargs
        assert kwargs["to"] == "ve-welcome@pathforge.eu"
        assert kwargs["name"] == "Welcome User"

    async def test_verify_email_invalid_token_returns_400(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(
            VERIFY_URL, json={"token": "no-such-token"},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    async def test_verify_email_expired_token_returns_400(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="ve-exp@pathforge.eu")
        user = await _fetch_user(db_session, "ve-exp@pathforge.eu")
        raw, hashed = generate_token()
        user.verification_token = hashed
        user.verification_sent_at = datetime.now(UTC) - timedelta(days=2)
        await db_session.flush()

        response = await client.post(VERIFY_URL, json={"token": raw})
        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    async def test_verify_email_clears_expired_token(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="ve-clear-exp@pathforge.eu")
        user = await _fetch_user(db_session, "ve-clear-exp@pathforge.eu")
        raw, hashed = generate_token()
        user.verification_token = hashed
        user.verification_sent_at = datetime.now(UTC) - timedelta(days=2)
        await db_session.flush()

        await client.post(VERIFY_URL, json={"token": raw})
        await db_session.refresh(user)
        assert user.verification_token is None

    async def test_verify_email_empty_token_returns_422(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(VERIFY_URL, json={"token": ""})
        assert response.status_code == 422


# ═════════════════════════════════════════════════════════════════
# RESEND VERIFICATION
# ═════════════════════════════════════════════════════════════════


class TestResendVerification:
    """POST /api/v1/auth/resend-verification."""

    async def test_resend_unverified_user_sends_email(
        self, client: AsyncClient,
    ) -> None:
        await _register(client, email="rv-ok@pathforge.eu")
        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_verification_email",
            new=email_mock,
        ):
            response = await client.post(
                RESEND_URL, json={"email": "rv-ok@pathforge.eu"},
            )

        assert response.status_code == 200
        email_mock.assert_called_once()
        assert email_mock.call_args.kwargs["to"] == "rv-ok@pathforge.eu"

    async def test_resend_unverified_updates_token_and_timestamp(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="rv-update@pathforge.eu")
        user = await _fetch_user(db_session, "rv-update@pathforge.eu")
        original_hash = user.verification_token
        assert original_hash is not None

        with patch(
            "app.api.v1.auth.EmailService.send_verification_email",
            new=MagicMock(return_value=True),
        ):
            response = await client.post(
                RESEND_URL, json={"email": "rv-update@pathforge.eu"},
            )

        assert response.status_code == 200
        await db_session.refresh(user)
        assert user.verification_token is not None
        assert user.verification_token != original_hash

    async def test_resend_already_verified_no_email(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        await _register(client, email="rv-verified@pathforge.eu")
        user = await _fetch_user(db_session, "rv-verified@pathforge.eu")
        user.is_verified = True
        user.verification_token = None
        await db_session.flush()

        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_verification_email",
            new=email_mock,
        ):
            response = await client.post(
                RESEND_URL, json={"email": "rv-verified@pathforge.eu"},
            )

        assert response.status_code == 200
        email_mock.assert_not_called()

    async def test_resend_nonexistent_user_returns_200_without_email(
        self, client: AsyncClient,
    ) -> None:
        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_verification_email",
            new=email_mock,
        ):
            response = await client.post(
                RESEND_URL, json={"email": "missing-user@pathforge.eu"},
            )

        assert response.status_code == 200
        email_mock.assert_not_called()

    async def test_resend_inactive_user_no_email(
        self, client: AsyncClient, db_session: AsyncSession,
    ) -> None:
        inactive = User(
            email="rv-inactive@pathforge.eu",
            hashed_password=hash_password(VALID_PASSWORD),
            full_name="Inactive",
            is_active=False,
            is_verified=False,
        )
        db_session.add(inactive)
        await db_session.flush()

        email_mock = MagicMock(return_value=True)
        with patch(
            "app.api.v1.auth.EmailService.send_verification_email",
            new=email_mock,
        ):
            response = await client.post(
                RESEND_URL, json={"email": inactive.email},
            )

        assert response.status_code == 200
        email_mock.assert_not_called()

    async def test_resend_invalid_email_returns_422(
        self, client: AsyncClient,
    ) -> None:
        response = await client.post(RESEND_URL, json={"email": "bad"})
        assert response.status_code == 422

    async def test_resend_response_message(self, client: AsyncClient) -> None:
        response = await client.post(
            RESEND_URL, json={"email": "any@pathforge.eu"},
        )
        assert response.status_code == 200
        assert "verification" in response.json()["message"].lower()
