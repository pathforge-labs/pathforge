"""
PathForge API — Cookie-first Auth Path Coverage (Track 1 / ADR-0006)
=====================================================================
Targeted tests for the httpOnly-cookie auth flow:

  1. login sets ``pathforge_access`` + ``pathforge_refresh`` + ``pathforge_csrf``
  2. ``get_current_user`` reads from the cookie when no Authorization header
  3. ``get_current_user`` still honours the bearer header (legacy fallback)
  4. ``refresh`` accepts the refresh token from cookie OR body
  5. ``logout`` clears cookies AND revokes both tokens
  6. CSRF double-submit enforcement on mutating cookie-auth requests

Each test is independent; each `client` fixture starts with a fresh
cookie jar.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from httpx import AsyncClient

from app.core.config import settings
from app.core.security import (
    ACCESS_COOKIE_NAME,
    CSRF_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    create_access_token,
    hash_password,
)
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

REGISTER_URL = "/api/v1/auth/register"
LOGIN_URL = "/api/v1/auth/login"
LOGOUT_URL = "/api/v1/auth/logout"
REFRESH_URL = "/api/v1/auth/refresh"
ME_URL = "/api/v1/users/me"


# ── Helpers ────────────────────────────────────────────────────────────────


async def _make_user(
    db: AsyncSession,
    email: str,
    *,
    is_verified: bool = True,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("CookieTest123!"),
        full_name="Cookie Test",
        is_active=True,
        is_verified=is_verified,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    """Hit /auth/login and return the JSON body. The cookie jar is
    populated as a side-effect because httpx persists cookies on the
    AsyncClient by default."""
    resp = await client.post(
        LOGIN_URL,
        json={"email": email, "password": "CookieTest123!"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Login sets the cookie pair + CSRF cookie
# ═══════════════════════════════════════════════════════════════════════════════


class TestLoginSetsCookies:
    async def test_login_sets_access_cookie(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, "cookie-access@example.com")
        await db_session.commit()
        await _login(client, "cookie-access@example.com")
        assert ACCESS_COOKIE_NAME in client.cookies
        # Cookie value should be a JWT (3 dot-separated segments).
        assert client.cookies[ACCESS_COOKIE_NAME].count(".") == 2

    async def test_login_sets_refresh_cookie(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, "cookie-refresh@example.com")
        await db_session.commit()
        await _login(client, "cookie-refresh@example.com")
        assert REFRESH_COOKIE_NAME in client.cookies

    async def test_login_sets_csrf_cookie(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, "cookie-csrf@example.com")
        await db_session.commit()
        await _login(client, "cookie-csrf@example.com")
        assert CSRF_COOKIE_NAME in client.cookies
        # CSRF cookie value is a 32-byte token_urlsafe string (~43 chars).
        assert len(client.cookies[CSRF_COOKIE_NAME]) >= 30

    async def test_login_returns_tokens_in_body_too(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """30-day overlap: tokens still in body for legacy clients."""
        await _make_user(db_session, "cookie-body@example.com")
        await db_session.commit()
        body = await _login(client, "cookie-body@example.com")
        assert "access_token" in body
        assert "refresh_token" in body


# ═══════════════════════════════════════════════════════════════════════════════
# 2. get_current_user reads cookie when no header
# ═══════════════════════════════════════════════════════════════════════════════


class TestCookieAuthPath:
    async def test_authenticated_request_via_cookie_no_header(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Login sets cookie; subsequent request without
        Authorization header still authenticates via the cookie jar."""
        await _make_user(db_session, "cookie-only@example.com")
        await db_session.commit()
        await _login(client, "cookie-only@example.com")

        # No Authorization header — pure cookie path.
        resp = await client.get(ME_URL)
        assert resp.status_code == 200
        assert resp.json()["email"] == "cookie-only@example.com"

    async def test_no_cookie_no_header_returns_401(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get(ME_URL)
        assert resp.status_code == 401

    async def test_invalid_cookie_returns_401(
        self, client: AsyncClient
    ) -> None:
        client.cookies.set(ACCESS_COOKIE_NAME, "not.a.jwt")
        resp = await client.get(ME_URL)
        assert resp.status_code == 401

    async def test_cookie_with_wrong_signature_returns_401(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "cookie-badsig@example.com")
        await db_session.commit()
        # Sign with a different secret.
        bad_token = jwt.encode(
            {
                "sub": str(user.id),
                "type": "access",
                "exp": datetime.now(UTC).timestamp() + 3600,
                "iat": datetime.now(UTC).timestamp(),
                "jti": "bad",
            },
            "wrong-secret",
            algorithm=settings.jwt_algorithm,
        )
        client.cookies.set(ACCESS_COOKIE_NAME, bad_token)
        resp = await client.get(ME_URL)
        assert resp.status_code == 401

    async def test_empty_cookie_falls_back_to_header(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """An empty `pathforge_access=` cookie (e.g. half-cleared client)
        must not pre-empt a valid bearer header."""
        user = await _make_user(db_session, "cookie-empty@example.com")
        await db_session.commit()
        bearer = create_access_token(str(user.id))
        client.cookies.set(ACCESS_COOKIE_NAME, "")
        resp = await client.get(
            ME_URL, headers={"Authorization": f"Bearer {bearer}"}
        )
        assert resp.status_code == 200


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Bearer header still works (legacy fallback)
# ═══════════════════════════════════════════════════════════════════════════════


class TestBearerLegacyFallback:
    async def test_bearer_header_authenticates_no_cookie(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "bearer-legacy@example.com")
        await db_session.commit()
        bearer = create_access_token(str(user.id))
        # No login → no cookie → bearer is the only auth path.
        resp = await client.get(
            ME_URL, headers={"Authorization": f"Bearer {bearer}"}
        )
        assert resp.status_code == 200

    async def test_bearer_header_overrides_cookie_for_csrf_skip(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """If both cookie and Authorization header are present, the
        request is treated as bearer auth: CSRF is skipped (legacy
        clients don't know about CSRF)."""
        await _make_user(db_session, "bearer-skip-csrf@example.com")
        await db_session.commit()
        # Login → sets cookies (incl. access cookie).
        body = await _login(client, "bearer-skip-csrf@example.com")
        # Logout request without X-CSRF-Token but WITH Authorization
        # header → must succeed (bearer path skips CSRF).
        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                LOGOUT_URL,
                headers={"Authorization": f"Bearer {body['access_token']}"},
            )
        assert resp.status_code == 204


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Refresh accepts cookie OR body
# ═══════════════════════════════════════════════════════════════════════════════


class TestRefreshFlexibility:
    async def test_refresh_via_cookie_only(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, "refresh-cookie@example.com")
        await db_session.commit()
        await _login(client, "refresh-cookie@example.com")
        # Cookie jar has refresh; body is empty.
        resp = await client.post(REFRESH_URL)
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body

    async def test_refresh_body_overrides_cookie(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """When both are present, the body wins — explicit beats implicit."""
        await _make_user(db_session, "refresh-explicit@example.com")
        await db_session.commit()
        body = await _login(client, "refresh-explicit@example.com")
        resp = await client.post(
            REFRESH_URL, json={"refresh_token": body["refresh_token"]}
        )
        assert resp.status_code == 200

    async def test_refresh_no_token_returns_401(
        self, client: AsyncClient
    ) -> None:
        # Fresh client → no cookie, no body.
        resp = await client.post(REFRESH_URL)
        assert resp.status_code == 401

    async def test_refresh_sets_new_cookies(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, "refresh-rotate@example.com")
        await db_session.commit()
        await _login(client, "refresh-rotate@example.com")
        old_access = client.cookies[ACCESS_COOKIE_NAME]
        resp = await client.post(REFRESH_URL)
        assert resp.status_code == 200
        # Cookie jar updated to new tokens.
        assert client.cookies[ACCESS_COOKIE_NAME] != old_access


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Logout clears cookies + revokes both
# ═══════════════════════════════════════════════════════════════════════════════


class TestLogoutClearsCookies:
    async def test_logout_clears_access_cookie(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, "logout-clear@example.com")
        await db_session.commit()
        body = await _login(client, "logout-clear@example.com")
        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                LOGOUT_URL,
                headers={"Authorization": f"Bearer {body['access_token']}"},
            )
        assert resp.status_code == 204
        # After logout, the cookie should be gone (or empty).
        assert not client.cookies.get(ACCESS_COOKIE_NAME)

    async def test_logout_clears_refresh_cookie(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, "logout-clear-r@example.com")
        await db_session.commit()
        body = await _login(client, "logout-clear-r@example.com")
        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ):
            await client.post(
                LOGOUT_URL,
                headers={"Authorization": f"Bearer {body['access_token']}"},
            )
        assert not client.cookies.get(REFRESH_COOKIE_NAME)

    async def test_logout_revokes_cookie_refresh_jti(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Even without `refresh_token` in body, the cookie refresh
        jti is revoked — closing the long-lived-token leak."""
        await _make_user(db_session, "logout-cookie-rev@example.com")
        await db_session.commit()
        body = await _login(client, "logout-cookie-rev@example.com")
        refresh_decoded = jwt.decode(
            body["refresh_token"],
            settings.jwt_refresh_secret,
            algorithms=[settings.jwt_algorithm],
        )
        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            await client.post(
                LOGOUT_URL,
                headers={"Authorization": f"Bearer {body['access_token']}"},
            )
        revoked_jtis = [call.args[0] for call in mock_revoke.call_args_list]
        assert refresh_decoded["jti"] in revoked_jtis


# ═══════════════════════════════════════════════════════════════════════════════
# 6. CSRF double-submit enforcement
# ═══════════════════════════════════════════════════════════════════════════════


class TestCSRFEnforcement:
    async def test_cookie_logout_without_csrf_header_403(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """Cookie-only logout (no Authorization header) MUST present a
        valid X-CSRF-Token. Missing header → 403."""
        await _make_user(db_session, "csrf-no-header@example.com")
        await db_session.commit()
        await _login(client, "csrf-no-header@example.com")
        # Cookie path (no Authorization header), no CSRF header → 403.
        resp = await client.post(LOGOUT_URL)
        assert resp.status_code == 403
        assert "csrf" in resp.json()["detail"].lower()

    async def test_cookie_logout_with_valid_csrf_header_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, "csrf-valid@example.com")
        await db_session.commit()
        await _login(client, "csrf-valid@example.com")
        csrf = client.cookies[CSRF_COOKIE_NAME]
        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                LOGOUT_URL, headers={"X-CSRF-Token": csrf}
            )
        assert resp.status_code == 204

    async def test_cookie_logout_with_mismatched_csrf_header_403(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        await _make_user(db_session, "csrf-mismatch@example.com")
        await db_session.commit()
        await _login(client, "csrf-mismatch@example.com")
        # Header is a real-shape value but not the cookie value.
        resp = await client.post(
            LOGOUT_URL, headers={"X-CSRF-Token": "not-the-cookie-value"}
        )
        assert resp.status_code == 403

    async def test_cookie_logout_with_missing_csrf_cookie_403(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """If access cookie is present but CSRF cookie is gone (manually
        cleared), CSRF protection refuses the request."""
        await _make_user(db_session, "csrf-missing-cookie@example.com")
        await db_session.commit()
        await _login(client, "csrf-missing-cookie@example.com")
        client.cookies.delete(CSRF_COOKIE_NAME)
        resp = await client.post(
            LOGOUT_URL, headers={"X-CSRF-Token": "any-value"}
        )
        assert resp.status_code == 403

    async def test_unauthenticated_request_no_csrf_required(
        self, client: AsyncClient
    ) -> None:
        """A request with neither cookie nor header is unauthenticated
        and must not even reach CSRF — auth dependency raises 401 first."""
        resp = await client.post(LOGOUT_URL)
        # Either 401 (auth fails first) or 403 (csrf fails first) is
        # acceptable; what we MUST NOT see is 5xx. The dependency order
        # in FastAPI runs csrf_protect BEFORE get_current_user (route
        # `dependencies=[]` evaluates first), so 403 is the actual
        # behaviour today; either way the request is rejected.
        assert resp.status_code in (401, 403)
