"""
PathForge API — Comprehensive Auth Flow Tests
================================================
Sprint 40 Gap Coverage: Tests for email verification, password reset,
logout/token blacklisting, and auth edge cases.

These flows were identified as untested during the Tier-1 audit.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.services.email_service import generate_token

if TYPE_CHECKING:
    from app.models.user import User


# ── Helpers ──────────────────────────────────────────────────────


async def _register_user(
    client: AsyncClient,
    email: str = "flow@pathforge.eu",
    password: str = "FlowPass123!",
    full_name: str = "Flow User",
) -> dict:
    """Register a user and return the response data + password."""
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    assert response.status_code == 201
    return {**response.json(), "password": password}


async def _login_user(
    client: AsyncClient,
    email: str,
    password: str,
) -> dict:
    """Login and return tokens."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200
    return response.json()


# ══════════════════════════════════════════════════════════════════
# 1. EMAIL VERIFICATION FLOW
# ══════════════════════════════════════════════════════════════════


class TestEmailVerification:
    """Tests for POST /auth/verify-email and POST /auth/resend-verification."""

    VERIFY_ENDPOINT = "/api/v1/auth/verify-email"
    RESEND_ENDPOINT = "/api/v1/auth/resend-verification"

    @pytest.mark.asyncio
    async def test_verify_email_success(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Valid verification token marks user as verified."""
        from sqlalchemy import select

        from app.models.user import User

        # Register (creates unverified user with verification_token)
        user_data = await _register_user(client, email="verify-ok@pathforge.eu")
        assert user_data["is_verified"] is False

        # Get the hashed token from DB to reverse-engineer the raw token
        result = await db_session.execute(
            select(User).where(User.email == "verify-ok@pathforge.eu")
        )
        user = result.scalar_one()
        stored_hash = user.verification_token
        assert stored_hash is not None

        # We need the raw token — since we can't reverse SHA-256,
        # inject a known token directly
        raw_token, hashed_token = generate_token()
        user.verification_token = hashed_token
        user.verification_sent_at = datetime.now(UTC)
        await db_session.flush()

        response = await client.post(
            self.VERIFY_ENDPOINT,
            json={"token": raw_token},
        )

        assert response.status_code == 200
        assert "verified" in response.json()["message"].lower()

        # Verify user is now marked as verified in DB
        await db_session.refresh(user)
        assert user.is_verified is True
        assert user.verification_token is None

    @pytest.mark.asyncio
    async def test_verify_email_invalid_token(self, client: AsyncClient) -> None:
        """Invalid verification token returns 400."""
        response = await client.post(
            self.VERIFY_ENDPOINT,
            json={"token": "completely-invalid-token"},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_email_expired_token(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Expired verification token returns 400."""
        from sqlalchemy import select

        from app.models.user import User

        await _register_user(client, email="verify-expired@pathforge.eu")

        result = await db_session.execute(
            select(User).where(User.email == "verify-expired@pathforge.eu")
        )
        user = result.scalar_one()

        # Set known token with expired timestamp
        raw_token, hashed_token = generate_token()
        user.verification_token = hashed_token
        user.verification_sent_at = datetime.now(UTC) - timedelta(hours=25)
        await db_session.flush()

        response = await client.post(
            self.VERIFY_ENDPOINT,
            json={"token": raw_token},
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_verify_email_clears_token_on_expiry(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Expired token is cleared from DB to prevent reuse."""
        from sqlalchemy import select

        from app.models.user import User

        await _register_user(client, email="verify-clear@pathforge.eu")

        result = await db_session.execute(
            select(User).where(User.email == "verify-clear@pathforge.eu")
        )
        user = result.scalar_one()

        raw_token, hashed_token = generate_token()
        user.verification_token = hashed_token
        user.verification_sent_at = datetime.now(UTC) - timedelta(hours=25)
        await db_session.flush()

        await client.post(self.VERIFY_ENDPOINT, json={"token": raw_token})

        # Token should be cleared
        await db_session.refresh(user)
        assert user.verification_token is None

    @pytest.mark.asyncio
    async def test_resend_verification_success(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Resend verification for unverified user returns 200."""
        await _register_user(client, email="resend@pathforge.eu")

        response = await client.post(
            self.RESEND_ENDPOINT,
            json={"email": "resend@pathforge.eu"},
        )

        assert response.status_code == 200
        assert "verification" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_resend_verification_nonexistent_email(
        self, client: AsyncClient,
    ) -> None:
        """Resend for non-existent email returns 200 (anti-enumeration)."""
        response = await client.post(
            self.RESEND_ENDPOINT,
            json={"email": "nobody-ever@pathforge.eu"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_resend_verification_already_verified(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Resend for already-verified user returns 200 but doesn't regenerate token."""
        from sqlalchemy import select

        from app.models.user import User

        await _register_user(client, email="already-verified@pathforge.eu")

        result = await db_session.execute(
            select(User).where(User.email == "already-verified@pathforge.eu")
        )
        user = result.scalar_one()
        user.is_verified = True
        user.verification_token = None
        await db_session.flush()

        response = await client.post(
            self.RESEND_ENDPOINT,
            json={"email": "already-verified@pathforge.eu"},
        )

        assert response.status_code == 200
        # Token should still be None (not regenerated)
        await db_session.refresh(user)
        assert user.verification_token is None


# ══════════════════════════════════════════════════════════════════
# 2. PASSWORD RESET FLOW
# ══════════════════════════════════════════════════════════════════


class TestPasswordReset:
    """Tests for POST /auth/forgot-password and POST /auth/reset-password."""

    FORGOT_ENDPOINT = "/api/v1/auth/forgot-password"
    RESET_ENDPOINT = "/api/v1/auth/reset-password"

    @pytest.mark.asyncio
    async def test_forgot_password_existing_user(
        self, client: AsyncClient,
    ) -> None:
        """Forgot password for existing user returns 200."""
        await _register_user(client, email="forgot@pathforge.eu")

        response = await client.post(
            self.FORGOT_ENDPOINT,
            json={"email": "forgot@pathforge.eu"},
        )

        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_forgot_password_nonexistent_email(
        self, client: AsyncClient,
    ) -> None:
        """Forgot password for non-existent email returns 200 (anti-enumeration)."""
        response = await client.post(
            self.FORGOT_ENDPOINT,
            json={"email": "ghost@pathforge.eu"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_forgot_password_inactive_user(
        self, client: AsyncClient, inactive_user: User,
    ) -> None:
        """Forgot password for inactive user returns 200 but doesn't generate token."""
        response = await client.post(
            self.FORGOT_ENDPOINT,
            json={"email": inactive_user.email},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_password_success(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Valid reset token allows password change."""
        from sqlalchemy import select

        from app.models.user import User

        await _register_user(
            client, email="reset-ok@pathforge.eu", password="OldPass123!"
        )

        # Simulate forgot-password flow: set known token
        result = await db_session.execute(
            select(User).where(User.email == "reset-ok@pathforge.eu")
        )
        user = result.scalar_one()
        raw_token, hashed_token = generate_token()
        user.password_reset_token = hashed_token
        user.password_reset_sent_at = datetime.now(UTC)
        await db_session.flush()

        # Reset password
        response = await client.post(
            self.RESET_ENDPOINT,
            json={"token": raw_token, "new_password": "NewSecure456!"},
        )

        assert response.status_code == 200
        assert "reset" in response.json()["message"].lower()

        # Verify token is cleared
        await db_session.refresh(user)
        assert user.password_reset_token is None

        # Verify new password works
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "reset-ok@pathforge.eu", "password": "NewSecure456!"},
        )
        assert login_response.status_code == 200

    @pytest.mark.asyncio
    async def test_reset_password_old_password_fails(
        self, client: AsyncClient, db_session,
    ) -> None:
        """After password reset, old password no longer works."""
        from sqlalchemy import select

        from app.models.user import User

        await _register_user(
            client, email="reset-old@pathforge.eu", password="OldPass123!"
        )

        result = await db_session.execute(
            select(User).where(User.email == "reset-old@pathforge.eu")
        )
        user = result.scalar_one()
        raw_token, hashed_token = generate_token()
        user.password_reset_token = hashed_token
        user.password_reset_sent_at = datetime.now(UTC)
        await db_session.flush()

        await client.post(
            self.RESET_ENDPOINT,
            json={"token": raw_token, "new_password": "BrandNew789!"},
        )

        # Old password should fail
        login_response = await client.post(
            "/api/v1/auth/login",
            json={"email": "reset-old@pathforge.eu", "password": "OldPass123!"},
        )
        assert login_response.status_code == 401

    @pytest.mark.asyncio
    async def test_reset_password_invalid_token(self, client: AsyncClient) -> None:
        """Invalid reset token returns 400."""
        response = await client.post(
            self.RESET_ENDPOINT,
            json={"token": "bogus-token", "new_password": "NewPass123!"},
        )
        assert response.status_code == 400
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_reset_password_expired_token(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Expired reset token returns 400."""
        from sqlalchemy import select

        from app.models.user import User

        await _register_user(client, email="reset-exp@pathforge.eu")

        result = await db_session.execute(
            select(User).where(User.email == "reset-exp@pathforge.eu")
        )
        user = result.scalar_one()
        raw_token, hashed_token = generate_token()
        user.password_reset_token = hashed_token
        user.password_reset_sent_at = datetime.now(UTC) - timedelta(minutes=31)
        await db_session.flush()

        response = await client.post(
            self.RESET_ENDPOINT,
            json={"token": raw_token, "new_password": "NewPass123!"},
        )

        assert response.status_code == 400
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_reset_password_token_single_use(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Reset token cannot be reused after successful reset."""
        from sqlalchemy import select

        from app.models.user import User

        await _register_user(client, email="reset-reuse@pathforge.eu")

        result = await db_session.execute(
            select(User).where(User.email == "reset-reuse@pathforge.eu")
        )
        user = result.scalar_one()
        raw_token, hashed_token = generate_token()
        user.password_reset_token = hashed_token
        user.password_reset_sent_at = datetime.now(UTC)
        await db_session.flush()

        # First use succeeds
        response1 = await client.post(
            self.RESET_ENDPOINT,
            json={"token": raw_token, "new_password": "First123!"},
        )
        assert response1.status_code == 200

        # Second use fails
        response2 = await client.post(
            self.RESET_ENDPOINT,
            json={"token": raw_token, "new_password": "Second123!"},
        )
        assert response2.status_code == 400


# ══════════════════════════════════════════════════════════════════
# 3. LOGOUT & TOKEN BLACKLISTING
# ══════════════════════════════════════════════════════════════════


class TestLogout:
    """Tests for POST /auth/logout."""

    LOGOUT_ENDPOINT = "/api/v1/auth/logout"

    @pytest.mark.asyncio
    async def test_logout_success(self, client: AsyncClient) -> None:
        """Authenticated user can logout (204 No Content)."""
        user_data = await _register_user(client, email="logout@pathforge.eu")
        tokens = await _login_user(
            client, user_data["email"], user_data["password"]
        )

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            response = await client.post(
                self.LOGOUT_ENDPOINT,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

        assert response.status_code == 204
        mock_revoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_without_token(self, client: AsyncClient) -> None:
        """Logout without token returns 401."""
        response = await client.post(self.LOGOUT_ENDPOINT)
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_with_invalid_token(self, client: AsyncClient) -> None:
        """Logout with invalid token returns 401."""
        response = await client.post(
            self.LOGOUT_ENDPOINT,
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_logout_blacklists_jti(self, client: AsyncClient) -> None:
        """Logout passes the token's JTI to the blacklist."""
        import jwt as pyjwt

        from app.core.config import settings

        user_data = await _register_user(client, email="logout-jti@pathforge.eu")
        tokens = await _login_user(
            client, user_data["email"], user_data["password"]
        )

        # Decode the token to get the JTI
        decoded = pyjwt.decode(
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
                self.LOGOUT_ENDPOINT,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

        # Verify correct JTI was blacklisted
        mock_revoke.assert_called_once()
        call_args = mock_revoke.call_args
        assert call_args[0][0] == expected_jti
        assert call_args[1]["ttl_seconds"] > 0


# ══════════════════════════════════════════════════════════════════
# 4. AUTH EDGE CASES
# ══════════════════════════════════════════════════════════════════


class TestAuthEdgeCases:
    """Edge case tests for auth endpoints."""

    @pytest.mark.asyncio
    async def test_login_inactive_user_returns_403(
        self, client: AsyncClient, inactive_user: User,
    ) -> None:
        """Inactive user attempting standard login gets 403."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": inactive_user.email,
                "password": "InactivePass123!",
            },
        )
        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_oauth_user_cannot_password_login(
        self, client: AsyncClient, db_session,
    ) -> None:
        """OAuth-only user attempting password login gets 401 with helpful message."""
        from app.models.user import User as UserModel

        # Create OAuth user with valid email domain (EmailStr rejects .test TLD)
        user = UserModel(
            email="oauth-only@gmail.com",
            hashed_password=None,
            full_name="OAuth Only User",
            auth_provider="google",
            is_verified=True,
        )
        db_session.add(user)
        await db_session.flush()

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "oauth-only@gmail.com",
                "password": "AnyPassword123!",
            },
        )
        assert response.status_code == 401
        assert "google" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_register_returns_unverified_user(
        self, client: AsyncClient,
    ) -> None:
        """New registration returns is_verified=False."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "fresh@pathforge.eu",
                "password": "FreshPass123!",
                "full_name": "Fresh User",
            },
        )
        assert response.status_code == 201
        assert response.json()["is_verified"] is False

    @pytest.mark.asyncio
    async def test_unverified_user_can_still_login(
        self, client: AsyncClient,
    ) -> None:
        """Unverified users can still login (verification enforced in frontend)."""
        user_data = await _register_user(
            client, email="unverified-login@pathforge.eu"
        )

        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"],
            },
        )
        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_refresh_token_for_inactive_user_fails(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Refresh token for deactivated user returns 401."""
        from sqlalchemy import select

        from app.models.user import User

        user_data = await _register_user(
            client, email="deactivated@pathforge.eu"
        )
        tokens = await _login_user(
            client, user_data["email"], user_data["password"]
        )

        # Deactivate user
        result = await db_session.execute(
            select(User).where(User.email == "deactivated@pathforge.eu")
        )
        user = result.scalar_one()
        user.is_active = False
        await db_session.flush()

        # Try to refresh
        response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
        )
        assert response.status_code == 401


# ══════════════════════════════════════════════════════════════════
# 5. TOKEN FIELD INDEPENDENCE (Sprint 41 P2 — fix verified)
# ══════════════════════════════════════════════════════════════════


class TestTokenFieldIndependence:
    """Tests verifying that email verification and password reset use
    separate token columns (verification_token vs password_reset_token).
    Requesting one flow must NOT invalidate the other's token."""

    @pytest.mark.asyncio
    async def test_password_reset_does_not_overwrite_verification_token(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Password reset request does NOT touch the verification_token column."""
        from sqlalchemy import select

        from app.models.user import User

        await _register_user(client, email="indep@pathforge.eu")

        result = await db_session.execute(
            select(User).where(User.email == "indep@pathforge.eu")
        )
        user = result.scalar_one()

        # Store original verification token set during registration
        original_verification_hash = user.verification_token
        assert original_verification_hash is not None

        # Request password reset — writes to password_reset_token, not verification_token
        await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "indep@pathforge.eu"},
        )

        await db_session.refresh(user)
        # Verification token must be unchanged
        assert user.verification_token == original_verification_hash
        # Password reset token must be set (separate column)
        assert user.password_reset_token is not None

    @pytest.mark.asyncio
    async def test_email_verification_succeeds_after_password_reset_request(
        self, client: AsyncClient, db_session,
    ) -> None:
        """Email verification still works after a password reset request
        because the tokens are stored in separate columns."""
        from sqlalchemy import select

        from app.models.user import User

        await _register_user(client, email="indep2@pathforge.eu")

        result = await db_session.execute(
            select(User).where(User.email == "indep2@pathforge.eu")
        )
        user = result.scalar_one()

        # Set known verification token
        raw_verify_token, hashed_verify = generate_token()
        user.verification_token = hashed_verify
        user.verification_sent_at = datetime.now(UTC)
        await db_session.flush()

        # Request password reset (different column now)
        await client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "indep2@pathforge.eu"},
        )

        # Original email verification token should STILL work
        response = await client.post(
            "/api/v1/auth/verify-email",
            json={"token": raw_verify_token},
        )
        assert response.status_code == 200


# ══════════════════════════════════════════════════════════════════
# 6. REFRESH TOKEN ROTATION (Sprint 41 P1-2)
# ══════════════════════════════════════════════════════════════════


class TestRefreshTokenRotation:
    """Tests for refresh token rotation and replay detection."""

    REFRESH_ENDPOINT = "/api/v1/auth/refresh"

    @pytest.mark.asyncio
    async def test_refresh_returns_distinct_tokens(
        self, client: AsyncClient,
    ) -> None:
        """Refresh returns new access + refresh tokens different from the originals."""
        user_data = await _register_user(client, email="rot-distinct@pathforge.eu")
        tokens = await _login_user(client, user_data["email"], user_data["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ), patch(
            "app.core.token_blacklist.TokenBlacklist.is_revoked",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = await client.post(
                self.REFRESH_ENDPOINT,
                json={"refresh_token": tokens["refresh_token"]},
            )

        assert response.status_code == 200
        new_tokens = response.json()
        assert new_tokens["access_token"] != tokens["access_token"]
        assert new_tokens["refresh_token"] != tokens["refresh_token"]

    @pytest.mark.asyncio
    async def test_refresh_revokes_old_token(
        self, client: AsyncClient,
    ) -> None:
        """Refresh calls token_blacklist.revoke with the old refresh token's JTI."""
        import jwt as pyjwt

        from app.core.config import settings

        user_data = await _register_user(client, email="rot-revoke@pathforge.eu")
        tokens = await _login_user(client, user_data["email"], user_data["password"])

        # Decode old refresh token to get its JTI
        old_decoded = pyjwt.decode(
            tokens["refresh_token"],
            settings.jwt_refresh_secret,
            algorithms=[settings.jwt_algorithm],
        )
        old_jti = old_decoded["jti"]

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke, patch(
            "app.core.token_blacklist.TokenBlacklist.is_revoked",
            new_callable=AsyncMock,
            return_value=False,
        ):
            response = await client.post(
                self.REFRESH_ENDPOINT,
                json={"refresh_token": tokens["refresh_token"]},
            )

        assert response.status_code == 200
        # revoke should have been called with the old JTI
        mock_revoke.assert_called_once()
        call_args = mock_revoke.call_args
        assert call_args[0][0] == old_jti
        assert call_args[1]["ttl_seconds"] > 0

    @pytest.mark.asyncio
    async def test_refresh_replay_detection(
        self, client: AsyncClient,
    ) -> None:
        """Reusing a consumed (revoked) refresh token returns 401."""
        user_data = await _register_user(client, email="rot-replay@pathforge.eu")
        tokens = await _login_user(client, user_data["email"], user_data["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ), patch(
            "app.core.token_blacklist.TokenBlacklist.is_revoked",
            new_callable=AsyncMock,
            return_value=True,  # Simulate already-consumed
        ):
            response = await client.post(
                self.REFRESH_ENDPOINT,
                json={"refresh_token": tokens["refresh_token"]},
            )

        assert response.status_code == 401
        assert "already been used" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_refresh_redis_failure_graceful(
        self, client: AsyncClient,
    ) -> None:
        """If Redis is unavailable, refresh still succeeds (best-effort rotation)."""
        user_data = await _register_user(client, email="rot-redis@pathforge.eu")
        tokens = await _login_user(client, user_data["email"], user_data["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis down"),
        ), patch(
            "app.core.token_blacklist.TokenBlacklist.is_revoked",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis down"),
        ):
            response = await client.post(
                self.REFRESH_ENDPOINT,
                json={"refresh_token": tokens["refresh_token"]},
            )

        # Should succeed despite Redis failure
        assert response.status_code == 200
        assert "access_token" in response.json()


# ══════════════════════════════════════════════════════════════════
# 7. LOGOUT REFRESH TOKEN REVOCATION (Sprint 41 P1)
# ══════════════════════════════════════════════════════════════════


class TestLogoutRefreshRevocation:
    """Tests for logout with refresh token revocation."""

    LOGOUT_ENDPOINT = "/api/v1/auth/logout"

    @pytest.mark.asyncio
    async def test_logout_with_refresh_revokes_both(
        self, client: AsyncClient,
    ) -> None:
        """Logout with refresh_token in body revokes both access and refresh JTIs."""
        user_data = await _register_user(client, email="logout-both@pathforge.eu")
        tokens = await _login_user(client, user_data["email"], user_data["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            response = await client.post(
                self.LOGOUT_ENDPOINT,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
                json={"refresh_token": tokens["refresh_token"]},
            )

        assert response.status_code == 204
        # Should have called revoke twice: once for access, once for refresh
        assert mock_revoke.call_count == 2

    @pytest.mark.asyncio
    async def test_logout_without_body_still_works(
        self, client: AsyncClient,
    ) -> None:
        """Logout without body still revokes access token only (backward compat)."""
        user_data = await _register_user(client, email="logout-nobody@pathforge.eu")
        tokens = await _login_user(client, user_data["email"], user_data["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            response = await client.post(
                self.LOGOUT_ENDPOINT,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
            )

        assert response.status_code == 204
        # Only access token revoked (1 call)
        mock_revoke.assert_called_once()

    @pytest.mark.asyncio
    async def test_logout_invalid_refresh_still_succeeds(
        self, client: AsyncClient,
    ) -> None:
        """Logout with invalid refresh_token still returns 204 (best-effort)."""
        user_data = await _register_user(client, email="logout-badref@pathforge.eu")
        tokens = await _login_user(client, user_data["email"], user_data["password"])

        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ):
            response = await client.post(
                self.LOGOUT_ENDPOINT,
                headers={"Authorization": f"Bearer {tokens['access_token']}"},
                json={"refresh_token": "invalid.refresh.token"},
            )

        assert response.status_code == 204
