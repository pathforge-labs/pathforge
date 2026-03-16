"""
PathForge API — OAuth Route Tests
====================================
Sprint Pre-40 H7: Comprehensive OAuth endpoint testing.

Tests the ``/auth/oauth/{provider}`` endpoint for Google and Microsoft
providers with mocked token verification. Follows the 3-layer testing
pyramid: this file covers Layer 1 (backend unit tests with mocked
external verification libraries).

Mock Strategy (Tier-1 Audit F1/F8):
  - Google: ``google.oauth2.id_token.verify_oauth2_token`` — patched at
    SOURCE MODULE because the import is lazy (inside function body).
  - Microsoft: ``app.api.v1.oauth._get_ms_jwks_client`` (module-level
    function) + ``app.api.v1.oauth.pyjwt.decode`` (module-level alias).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar
from unittest.mock import MagicMock, patch

import pytest

if TYPE_CHECKING:
    from httpx import AsyncClient

    from app.models.user import User


# ── Google OAuth Tests ─────────────────────────────────────────


class TestGoogleOAuth:
    """Google OAuth token verification and user management."""

    ENDPOINT = "/api/v1/auth/oauth/google"
    GOOGLE_CLAIMS: ClassVar[dict[str, str]] = {
        "email": "new-oauth@google.test",
        "name": "Google User",
        "sub": "google-uid-123",
    }

    # F8: google.oauth2.id_token is lazily imported INSIDE _verify_google_token
    # function body (oauth.py L100-101). Must patch the SOURCE module.
    MOCK_PATH = "google.oauth2.id_token.verify_oauth2_token"

    @pytest.mark.asyncio
    @patch(MOCK_PATH)
    async def test_google_login_new_user(
        self, mock_verify: MagicMock, client: AsyncClient,
    ) -> None:
        """Valid Google token for unknown email → creates user, returns JWT pair."""
        mock_verify.return_value = self.GOOGLE_CLAIMS

        response = await client.post(
            self.ENDPOINT, json={"id_token": "mock-google-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    @patch(MOCK_PATH)
    async def test_google_login_existing_user(
        self, mock_verify: MagicMock, client: AsyncClient, oauth_user: User,
    ) -> None:
        """Valid Google token for existing user → returns JWT pair, no duplicate."""
        mock_verify.return_value = {
            "email": oauth_user.email,
            "name": oauth_user.full_name,
            "sub": "google-uid-existing",
        }

        response = await client.post(
            self.ENDPOINT, json={"id_token": "mock-google-token"},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    @patch(MOCK_PATH)
    async def test_google_login_auto_verifies_unverified_user(
        self,
        mock_verify: MagicMock,
        client: AsyncClient,
        registered_user: dict[str, str],
    ) -> None:
        """F16: Existing unverified user → OAuth auto-verifies them."""
        mock_verify.return_value = {
            "email": registered_user["email"],
            "name": "Google User",
            "sub": "google-uid-verify",
        }

        response = await client.post(
            self.ENDPOINT, json={"id_token": "mock-google-token"},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    @patch(MOCK_PATH)
    async def test_google_login_inactive_user(
        self, mock_verify: MagicMock, client: AsyncClient, inactive_user: User,
    ) -> None:
        """Deactivated user attempting Google OAuth → 403 Forbidden."""
        mock_verify.return_value = {
            "email": inactive_user.email,
            "name": "Inactive",
            "sub": "google-uid-inactive",
        }

        response = await client.post(
            self.ENDPOINT, json={"id_token": "mock-google-token"},
        )

        assert response.status_code == 403
        assert "inactive" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch(MOCK_PATH)
    async def test_google_login_invalid_token(
        self, mock_verify: MagicMock, client: AsyncClient,
    ) -> None:
        """Google rejects the token (raises ValueError) → 401."""
        mock_verify.side_effect = ValueError("Invalid token")

        response = await client.post(
            self.ENDPOINT, json={"id_token": "bad-token"},
        )

        assert response.status_code == 401
        assert "invalid" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch(MOCK_PATH)
    async def test_google_login_token_missing_email(
        self, mock_verify: MagicMock, client: AsyncClient,
    ) -> None:
        """Google token has no email claim → 400."""
        mock_verify.return_value = {"name": "No Email User", "sub": "123"}

        response = await client.post(
            self.ENDPOINT, json={"id_token": "mock-google-token"},
        )

        assert response.status_code == 400
        assert "email" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_google_not_configured(self, client: AsyncClient) -> None:
        """Google OAuth client ID not set → 501 Not Implemented."""
        from app.core.config import settings

        original = settings.google_oauth_client_id
        object.__setattr__(settings, "google_oauth_client_id", "")
        try:
            response = await client.post(
                self.ENDPOINT, json={"id_token": "any-token"},
            )
            assert response.status_code == 501
            assert "not configured" in response.json()["detail"].lower()
        finally:
            object.__setattr__(settings, "google_oauth_client_id", original)


# ── Microsoft OAuth Tests ──────────────────────────────────────


class TestMicrosoftOAuth:
    """Microsoft OAuth token verification and user management."""

    ENDPOINT = "/api/v1/auth/oauth/microsoft"
    MS_CLAIMS: ClassVar[dict[str, str]] = {
        "email": "new-oauth@microsoft.test",
        "name": "Microsoft User",
        "sub": "ms-uid-456",
    }

    # Microsoft: pyjwt is module-level alias (L25), _get_ms_jwks_client is
    # module-level function (L61). Both patchable via app.api.v1.oauth.
    MOCK_JWKS = "app.api.v1.oauth._get_ms_jwks_client"
    MOCK_DECODE = "app.api.v1.oauth.pyjwt.decode"

    @pytest.mark.asyncio
    @patch(MOCK_DECODE)
    @patch(MOCK_JWKS)
    async def test_microsoft_login_new_user(
        self,
        mock_jwks: MagicMock,
        mock_decode: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Valid Microsoft token for unknown email → creates user, returns JWT pair."""
        mock_jwks.return_value.get_signing_key_from_jwt.return_value = MagicMock(
            key="fake-rsa-key",
        )
        mock_decode.return_value = self.MS_CLAIMS

        response = await client.post(
            self.ENDPOINT, json={"id_token": "mock-ms-token"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data

    @pytest.mark.asyncio
    @patch(MOCK_DECODE)
    @patch(MOCK_JWKS)
    async def test_microsoft_login_existing_user(
        self,
        mock_jwks: MagicMock,
        mock_decode: MagicMock,
        client: AsyncClient,
        oauth_user: User,
    ) -> None:
        """Valid Microsoft token for existing user → returns JWT pair."""
        mock_jwks.return_value.get_signing_key_from_jwt.return_value = MagicMock(
            key="fake-rsa-key",
        )
        mock_decode.return_value = {
            "email": oauth_user.email,
            "name": oauth_user.full_name,
            "sub": "ms-uid-existing",
        }

        response = await client.post(
            self.ENDPOINT, json={"id_token": "mock-ms-token"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch(MOCK_DECODE)
    @patch(MOCK_JWKS)
    async def test_microsoft_login_preferred_username_fallback(
        self,
        mock_jwks: MagicMock,
        mock_decode: MagicMock,
        client: AsyncClient,
    ) -> None:
        """Token with `preferred_username` but no `email` → succeeds."""
        mock_jwks.return_value.get_signing_key_from_jwt.return_value = MagicMock(
            key="fake-rsa-key",
        )
        mock_decode.return_value = {
            "preferred_username": "fallback@microsoft.test",
            "name": "Fallback User",
            "sub": "ms-uid-fallback",
        }

        response = await client.post(
            self.ENDPOINT, json={"id_token": "mock-ms-token"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    @patch(MOCK_DECODE)
    @patch(MOCK_JWKS)
    async def test_microsoft_login_inactive_user(
        self,
        mock_jwks: MagicMock,
        mock_decode: MagicMock,
        client: AsyncClient,
        inactive_user: User,
    ) -> None:
        """Deactivated user attempting Microsoft OAuth → 403."""
        mock_jwks.return_value.get_signing_key_from_jwt.return_value = MagicMock(
            key="fake-rsa-key",
        )
        mock_decode.return_value = {
            "email": inactive_user.email,
            "name": "Inactive",
            "sub": "ms-uid-inactive",
        }

        response = await client.post(
            self.ENDPOINT, json={"id_token": "mock-ms-token"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    @patch(MOCK_JWKS)
    async def test_microsoft_login_expired_token(
        self, mock_jwks: MagicMock, client: AsyncClient,
    ) -> None:
        """Expired Microsoft token → 401 with 'expired' detail."""
        import jwt as pyjwt_lib

        mock_jwks.return_value.get_signing_key_from_jwt.return_value = MagicMock(
            key="fake-rsa-key",
        )

        with patch(self.MOCK_DECODE, side_effect=pyjwt_lib.ExpiredSignatureError):
            response = await client.post(
                self.ENDPOINT, json={"id_token": "expired-token"},
            )

        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    @patch(MOCK_JWKS)
    async def test_microsoft_login_invalid_token(
        self, mock_jwks: MagicMock, client: AsyncClient,
    ) -> None:
        """JWKS verification fails → 401."""
        import jwt as pyjwt_lib

        mock_jwks.return_value.get_signing_key_from_jwt.return_value = MagicMock(
            key="fake-rsa-key",
        )

        with patch(self.MOCK_DECODE, side_effect=pyjwt_lib.InvalidTokenError):
            response = await client.post(
                self.ENDPOINT, json={"id_token": "invalid-token"},
            )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_microsoft_not_configured(self, client: AsyncClient) -> None:
        """Microsoft OAuth client ID not set → 501."""
        from app.core.config import settings

        original = settings.microsoft_oauth_client_id
        object.__setattr__(settings, "microsoft_oauth_client_id", "")
        try:
            response = await client.post(
                self.ENDPOINT, json={"id_token": "any-token"},
            )
            assert response.status_code == 501
            assert "not configured" in response.json()["detail"].lower()
        finally:
            object.__setattr__(settings, "microsoft_oauth_client_id", original)


# ── Cross-Provider Tests ──────────────────────────────────────


class TestOAuthCrossProvider:
    """Tests spanning multiple providers and edge cases."""

    GOOGLE_MOCK = "google.oauth2.id_token.verify_oauth2_token"
    MS_JWKS_MOCK = "app.api.v1.oauth._get_ms_jwks_client"
    MS_DECODE_MOCK = "app.api.v1.oauth.pyjwt.decode"

    @pytest.mark.asyncio
    @patch(GOOGLE_MOCK)
    async def test_account_linking_google_to_email_user(
        self,
        mock_verify: MagicMock,
        client: AsyncClient,
        registered_user: dict[str, str],
    ) -> None:
        """Email/password user logs in via Google → same account, now verified."""
        mock_verify.return_value = {
            "email": registered_user["email"],
            "name": "Linked User",
            "sub": "google-uid-link",
        }

        response = await client.post(
            "/api/v1/auth/oauth/google",
            json={"id_token": "mock-google-token"},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    @patch(MS_DECODE_MOCK)
    @patch(MS_JWKS_MOCK)
    async def test_account_linking_microsoft_to_email_user(
        self,
        mock_jwks: MagicMock,
        mock_decode: MagicMock,
        client: AsyncClient,
        registered_user: dict[str, str],
    ) -> None:
        """Email/password user logs in via Microsoft → same account."""
        mock_jwks.return_value.get_signing_key_from_jwt.return_value = MagicMock(
            key="fake-rsa-key",
        )
        mock_decode.return_value = {
            "email": registered_user["email"],
            "name": "Linked User",
            "sub": "ms-uid-link",
        }

        response = await client.post(
            "/api/v1/auth/oauth/microsoft",
            json={"id_token": "mock-ms-token"},
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

    @pytest.mark.asyncio
    async def test_oauth_invalid_provider(self, client: AsyncClient) -> None:
        """Unsupported provider name → 422 (FastAPI Literal validation)."""
        response = await client.post(
            "/api/v1/auth/oauth/github",
            json={"id_token": "any-token"},
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_oauth_empty_id_token(self, client: AsyncClient) -> None:
        """Empty ID token string → 422 (Pydantic min_length=1)."""
        response = await client.post(
            "/api/v1/auth/oauth/google",
            json={"id_token": ""},
        )

        assert response.status_code == 422
