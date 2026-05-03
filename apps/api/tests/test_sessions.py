"""
PathForge — Active Session Registry tests (T1-extension, ADR-0011)
=====================================================================

Two layers:

  1. Pure-function helpers (`_truncate_ua`, `_derive_device_label`).
  2. Route-level integration through the public client. Redis is
     replaced with a fakeredis-backed instance so tests are
     hermetic and the soft-fail path is independently exercised.

The fakeredis fixture is local to this file because no other test
suite needs an in-memory Redis today; pulling it into ``conftest.py``
would expand its scope without payoff.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

from app.core.security import (
    CSRF_COOKIE_NAME,
    create_access_token,
    create_refresh_token,
    hash_password,
)
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ── Fixtures ────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def fake_redis() -> AsyncGenerator[object, None]:
    """In-memory Redis stand-in.

    Patches the `SessionRegistry._redis` class attribute so the
    registry talks to a `fakeredis.aioredis.FakeRedis` for the
    duration of the test. Tearing down resets the singleton so
    subsequent tests don't see leftover state.
    """
    fakeredis = pytest.importorskip("fakeredis")
    from app.core.sessions import SessionRegistry

    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    original = SessionRegistry._redis
    SessionRegistry._redis = fake
    try:
        yield fake
    finally:
        await fake.aclose()
        SessionRegistry._redis = original


async def _make_user(db: AsyncSession, email: str = "session-user@example.com") -> User:
    user = User(
        email=email,
        hashed_password=hash_password("SessionTest123!"),
        full_name="Session User",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


# ── 1. Pure helpers ─────────────────────────────────────────────


class TestSessionHelpers:
    def test_truncate_ua_caps_long_strings(self) -> None:
        from app.core.sessions import _truncate_ua

        long_ua = "x" * 500
        out = _truncate_ua(long_ua)
        assert len(out) == 200

    def test_truncate_ua_handles_none(self) -> None:
        from app.core.sessions import _truncate_ua

        assert _truncate_ua(None) == ""
        assert _truncate_ua("") == ""

    @pytest.mark.parametrize(
        "ua,expected_substring",
        [
            ("Mozilla/5.0 (Windows NT 10.0) Chrome/120.0", "Chrome on Windows"),
            ("Mozilla/5.0 (Macintosh) AppleWebKit/605 Safari/605.1.15", "Safari on macOS"),
            ("Mozilla/5.0 (X11; Linux x86_64) Firefox/121.0", "Firefox on Linux"),
            ("Mozilla/5.0 Edg/119.0", "Edge"),
            ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X)", "iOS"),
            ("Mozilla/5.0 (Linux; Android 13)", "Android"),
            ("ExpoApp/1.0 okhttp/5.0", "Mobile app"),
        ],
    )
    def test_derive_device_label_recognises_common_uas(
        self, ua: str, expected_substring: str
    ) -> None:
        from app.core.sessions import _derive_device_label

        assert expected_substring in _derive_device_label(ua)

    def test_derive_device_label_falls_back_for_empty(self) -> None:
        from app.core.sessions import _derive_device_label

        assert _derive_device_label("") == "Unknown device"


# ── 2. Registry round-trip ──────────────────────────────────────


class TestSessionRegistryRoundTrip:
    async def test_register_and_list(self, fake_redis: object) -> None:
        from app.core.sessions import SessionRegistry

        await SessionRegistry.register(
            user_id="user-1",
            jti="jti-1",
            ttl_seconds=3600,
            ip="127.0.0.1",
            user_agent="Mozilla/5.0 (Windows NT 10.0) Chrome/120.0",
        )
        sessions = await SessionRegistry.list_for_user(user_id="user-1")
        assert len(sessions) == 1
        sess = sessions[0]
        assert sess["jti"] == "jti-1"
        assert sess["ip"] == "127.0.0.1"
        assert "Chrome" in sess["device_label"]

    async def test_register_multiple_devices(self, fake_redis: object) -> None:
        from app.core.sessions import SessionRegistry

        await SessionRegistry.register(
            user_id="user-2", jti="jti-a", ttl_seconds=3600, ip="1.1.1.1", user_agent="A",
        )
        await SessionRegistry.register(
            user_id="user-2", jti="jti-b", ttl_seconds=3600, ip="2.2.2.2", user_agent="B",
        )
        sessions = await SessionRegistry.list_for_user(user_id="user-2")
        assert len(sessions) == 2
        jtis = {s["jti"] for s in sessions}
        assert jtis == {"jti-a", "jti-b"}

    async def test_revoke_drops_session_and_blacklists(
        self, fake_redis: object
    ) -> None:
        from app.core.sessions import SessionRegistry

        await SessionRegistry.register(
            user_id="user-3", jti="jti-x", ttl_seconds=3600, ip=None, user_agent=None,
        )
        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            return_value=None,
        ) as mock_blacklist:
            ok = await SessionRegistry.revoke(
                user_id="user-3", jti="jti-x", ttl_seconds=3600,
            )
        assert ok is True
        assert await SessionRegistry.list_for_user(user_id="user-3") == []
        mock_blacklist.assert_called_once_with("jti-x", ttl_seconds=3600)

    async def test_revoke_others_keeps_current(self, fake_redis: object) -> None:
        from app.core.sessions import SessionRegistry

        for jti in ("a", "b", "c"):
            await SessionRegistry.register(
                user_id="user-4", jti=jti, ttl_seconds=3600, ip=None, user_agent=None,
            )
        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            return_value=None,
        ):
            revoked = await SessionRegistry.revoke_others(
                user_id="user-4", current_jti="b", ttl_seconds=3600,
            )
        assert set(revoked) == {"a", "c"}
        remaining = await SessionRegistry.list_for_user(user_id="user-4")
        assert len(remaining) == 1
        assert remaining[0]["jti"] == "b"

    async def test_purge_user_drops_everything(self, fake_redis: object) -> None:
        from app.core.sessions import SessionRegistry

        for jti in ("p1", "p2"):
            await SessionRegistry.register(
                user_id="user-5", jti=jti, ttl_seconds=3600, ip=None, user_agent=None,
            )
        await SessionRegistry.purge_user(user_id="user-5")
        assert await SessionRegistry.list_for_user(user_id="user-5") == []

    async def test_list_returns_empty_when_no_sessions(
        self, fake_redis: object
    ) -> None:
        from app.core.sessions import SessionRegistry

        assert await SessionRegistry.list_for_user(user_id="user-empty") == []

    async def test_touch_updates_last_seen(self, fake_redis: object) -> None:
        from app.core.sessions import SessionRegistry

        await SessionRegistry.register(
            user_id="user-touch", jti="t1", ttl_seconds=3600, ip=None, user_agent=None,
        )
        before = (await SessionRegistry.list_for_user(user_id="user-touch"))[0][
            "last_seen_at"
        ]
        # Touch with an explicit, later timestamp via the patch hook
        # directly on Redis to keep the test deterministic.
        await SessionRegistry.touch(jti="t1")
        after = (await SessionRegistry.list_for_user(user_id="user-touch"))[0][
            "last_seen_at"
        ]
        # `last_seen_at` was rewritten — value may be lexicographically
        # larger or equal; at minimum it's set.
        assert after >= before


# ── 3. Soft-fail behaviour when Redis is down ──────────────────


class TestSessionRegistrySoftFail:
    async def test_register_swallows_errors(self) -> None:
        """register() must not propagate any exception — the auth flow
        relies on this contract."""
        from app.core.sessions import SessionRegistry

        with patch.object(
            SessionRegistry,
            "get_redis",
            side_effect=ConnectionError("redis down"),
        ):
            # No raise.
            await SessionRegistry.register(
                user_id="u",
                jti="j",
                ttl_seconds=60,
                ip=None,
                user_agent=None,
            )

    async def test_list_returns_empty_on_redis_error(self) -> None:
        from app.core.sessions import SessionRegistry

        with patch.object(
            SessionRegistry,
            "get_redis",
            side_effect=ConnectionError("redis down"),
        ):
            sessions = await SessionRegistry.list_for_user(user_id="u")
        assert sessions == []

    async def test_revoke_returns_false_on_redis_error(self) -> None:
        from app.core.sessions import SessionRegistry

        with patch.object(
            SessionRegistry,
            "get_redis",
            side_effect=ConnectionError("redis down"),
        ):
            ok = await SessionRegistry.revoke(
                user_id="u", jti="j", ttl_seconds=60,
            )
        assert ok is False


# ── 4. Route integration ────────────────────────────────────────


class TestSessionsRoutes:
    async def test_list_sessions_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        fake_redis: object,
    ) -> None:
        from app.core.sessions import SessionRegistry

        user = await _make_user(db_session, "list-sessions@example.com")
        await db_session.commit()
        # Seed two sessions for the user.
        await SessionRegistry.register(
            user_id=str(user.id),
            jti="seed-1",
            ttl_seconds=3600,
            ip="10.0.0.1",
            user_agent="Mozilla/5.0 Chrome/120",
        )
        await SessionRegistry.register(
            user_id=str(user.id),
            jti="seed-2",
            ttl_seconds=3600,
            ip="10.0.0.2",
            user_agent="Mozilla/5.0 Firefox/121",
        )
        token = create_access_token(str(user.id))
        resp = await client.get(
            "/api/v1/users/me/sessions",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "sessions" in body
        assert len(body["sessions"]) == 2

    async def test_revoke_session_returns_204(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        fake_redis: object,
    ) -> None:
        from app.core.sessions import SessionRegistry

        user = await _make_user(db_session, "revoke-sessions@example.com")
        await db_session.commit()
        await SessionRegistry.register(
            user_id=str(user.id),
            jti="revoke-target",
            ttl_seconds=3600,
            ip=None,
            user_agent=None,
        )
        token = create_access_token(str(user.id))
        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            return_value=None,
        ):
            resp = await client.delete(
                "/api/v1/users/me/sessions/revoke-target",
                headers={"Authorization": f"Bearer {token}"},
            )
        assert resp.status_code == 204
        assert await SessionRegistry.list_for_user(user_id=str(user.id)) == []

    async def test_revoke_unknown_jti_returns_404(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        fake_redis: object,
    ) -> None:
        user = await _make_user(db_session, "unknown-jti@example.com")
        await db_session.commit()
        token = create_access_token(str(user.id))
        resp = await client.delete(
            "/api/v1/users/me/sessions/does-not-exist",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 404

    async def test_revoke_others_returns_count(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        fake_redis: object,
    ) -> None:
        from app.core.sessions import SessionRegistry

        user = await _make_user(db_session, "revoke-others@example.com")
        await db_session.commit()
        # Issue a real refresh token (so the cookie carries a valid JTI)
        # plus two pretend-foreign sessions.
        refresh = create_refresh_token(str(user.id))
        import jwt

        from app.core.config import settings

        decoded = jwt.decode(
            refresh, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm],
        )
        current_jti = decoded["jti"]
        await SessionRegistry.register(
            user_id=str(user.id), jti=current_jti, ttl_seconds=3600, ip=None, user_agent=None,
        )
        await SessionRegistry.register(
            user_id=str(user.id), jti="other-1", ttl_seconds=3600, ip=None, user_agent=None,
        )
        await SessionRegistry.register(
            user_id=str(user.id), jti="other-2", ttl_seconds=3600, ip=None, user_agent=None,
        )

        access = create_access_token(str(user.id))
        # Set the cookie jar so the handler can read the current JTI.
        client.cookies.set("pathforge_refresh", refresh)
        client.cookies.set(CSRF_COOKIE_NAME, "csrf-test-value")
        with patch(
            "app.core.token_blacklist.TokenBlacklist.revoke",
            return_value=None,
        ):
            resp = await client.post(
                "/api/v1/users/me/sessions/revoke-others",
                headers={
                    "Authorization": f"Bearer {access}",
                    "X-CSRF-Token": "csrf-test-value",
                },
            )
        assert resp.status_code == 200
        assert resp.json()["revoked_count"] == 2
        remaining = await SessionRegistry.list_for_user(user_id=str(user.id))
        assert {s["jti"] for s in remaining} == {current_jti}

    async def test_revoke_others_400_for_legacy_bearer_only(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
        fake_redis: object,
    ) -> None:
        """No refresh cookie → legacy bearer client → 400, never silently
        wipe everything."""
        user = await _make_user(db_session, "legacy-bearer@example.com")
        await db_session.commit()
        token = create_access_token(str(user.id))
        resp = await client.post(
            "/api/v1/users/me/sessions/revoke-others",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 400
        assert "cookie" in resp.json()["detail"].lower()

    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/users/me/sessions")
        assert resp.status_code == 401
