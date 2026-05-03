"""
PathForge — SSO Session-Revoke Webhook tests (T1-extension part 2, Sprint 62)
===============================================================================

Covers ``app/core/sso_session_revoke.py`` — the admin partner endpoint
that force-logouts a PathForge user on offboarding.

Test plan
---------

1. Signature gate
   - Missing ``X-PathForge-Signature`` → 401
   - Wrong signature → 401
   - Empty ``sso_webhook_secret`` setting → 401 (fail-closed)
   - Valid signature passes through

2. Payload validation
   - ``user_id`` absent → 422
   - ``user_id`` not a valid UUID4 → 422

3. Successful logout
   - User with N active sessions → sessions blacklisted + registry purged →
     200 ``{"revoked_count": N, "user_id": "…"}``

4. No-op for a user with no sessions
   - 200 ``{"revoked_count": 0, …}``

5. Redis unavailability
   - ``list_for_user`` raises → 503

6. Partial blacklist failures
   - Some blacklist writes fail but at least one succeeds →
     200 with ``revoked_count == successful_count``
   - All blacklist writes fail → 503

7. ``_verify_signature`` unit tests (pure-function, synchronous)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from collections.abc import AsyncGenerator
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient

_ENDPOINT = "/api/v1/internal/sso/logout"
_TEST_SECRET = "sso-webhook-test-secret-32chars!x"
_VALID_UUID = str(uuid.uuid4())


# ── Helpers ───────────────────────────────────────────────────────────


def _sign(secret: str, body: bytes) -> str:
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def _body(user_id: str = _VALID_UUID, reason: str = "offboarding") -> bytes:
    return json.dumps({"user_id": user_id, "reason": reason}).encode()


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def sso_secret(monkeypatch: pytest.MonkeyPatch) -> str:
    from app.core.config import settings

    monkeypatch.setattr(settings, "sso_webhook_secret", _TEST_SECRET, raising=False)
    return _TEST_SECRET


@pytest_asyncio.fixture
async def fake_redis() -> AsyncGenerator[object, None]:
    """In-memory Redis that backs ``SessionRegistry`` during the test."""
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


async def _seed_session(
    fake_redis: Any,
    user_id: str,
    jti: str,
    ttl: int = 86_400,
) -> None:
    """Seed a minimal session into the fake Redis."""
    from app.core.sessions import _meta_key, _user_set_key

    await fake_redis.sadd(_user_set_key(user_id), jti)
    await fake_redis.expire(_user_set_key(user_id), ttl)
    meta = {
        "user_id": user_id,
        "jti": jti,
        "created_at": "2026-04-27T00:00:00+00:00",
        "last_seen_at": "2026-04-27T00:00:00+00:00",
        "ip": "127.0.0.1",
        "user_agent": "TestAgent/1.0",
        "device_label": "Unknown",
    }
    await fake_redis.hset(_meta_key(jti), mapping=meta)
    await fake_redis.expire(_meta_key(jti), ttl)


# ── 1. Signature gate ─────────────────────────────────────────────────


class TestSignatureGate:
    async def test_missing_signature_returns_401(
        self, client: AsyncClient, sso_secret: str,
    ) -> None:
        body = _body()
        resp = await client.post(
            _ENDPOINT,
            content=body,
            headers={"Content-Type": "application/json"},
        )
        assert resp.status_code == 401

    async def test_wrong_signature_returns_401(
        self, client: AsyncClient, sso_secret: str,
    ) -> None:
        body = _body()
        resp = await client.post(
            _ENDPOINT,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-PathForge-Signature": "deadbeef" * 8,
            },
        )
        assert resp.status_code == 401

    async def test_empty_secret_rejects_all_requests(
        self, client: AsyncClient, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unconfigured secret → fail-closed (even a correctly-signed request is rejected)."""
        from app.core.config import settings

        monkeypatch.setattr(settings, "sso_webhook_secret", "", raising=False)
        body = _body()
        sig = _sign("", body)
        resp = await client.post(
            _ENDPOINT,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-PathForge-Signature": sig,
            },
        )
        assert resp.status_code == 401

    async def test_valid_signature_passes_through(
        self,
        client: AsyncClient,
        sso_secret: str,
        fake_redis: Any,
    ) -> None:
        body = _body()
        sig = _sign(sso_secret, body)
        resp = await client.post(
            _ENDPOINT,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-PathForge-Signature": sig,
            },
        )
        assert resp.status_code == 200


# ── 2. Payload validation ─────────────────────────────────────────────


class TestPayloadValidation:
    async def test_missing_user_id_returns_422(
        self, client: AsyncClient, sso_secret: str,
    ) -> None:
        body = json.dumps({"reason": "offboarding"}).encode()
        sig = _sign(sso_secret, body)
        resp = await client.post(
            _ENDPOINT,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-PathForge-Signature": sig,
            },
        )
        assert resp.status_code == 422

    async def test_invalid_uuid_returns_422(
        self, client: AsyncClient, sso_secret: str,
    ) -> None:
        body = json.dumps({"user_id": "not-a-uuid"}).encode()
        sig = _sign(sso_secret, body)
        resp = await client.post(
            _ENDPOINT,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-PathForge-Signature": sig,
            },
        )
        assert resp.status_code == 422

    async def test_unknown_fields_ignored(
        self,
        client: AsyncClient,
        sso_secret: str,
        fake_redis: Any,
    ) -> None:
        """``extra="ignore"`` on the schema — unknown fields must not cause 422."""
        body = json.dumps({
            "user_id": _VALID_UUID,
            "reason": "offboarding",
            "unknown_future_field": "value",
        }).encode()
        sig = _sign(sso_secret, body)
        resp = await client.post(
            _ENDPOINT,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-PathForge-Signature": sig,
            },
        )
        assert resp.status_code == 200


# ── 3. Successful logout ──────────────────────────────────────────────


class TestSuccessfulLogout:
    async def test_revokes_all_sessions_for_user(
        self,
        client: AsyncClient,
        sso_secret: str,
        fake_redis: Any,
    ) -> None:
        user_id = str(uuid.uuid4())
        jti_a = str(uuid.uuid4())
        jti_b = str(uuid.uuid4())
        await _seed_session(fake_redis, user_id, jti_a)
        await _seed_session(fake_redis, user_id, jti_b)

        body = _body(user_id=user_id)
        sig = _sign(sso_secret, body)

        with patch(
            "app.core.token_blacklist.token_blacklist.revoke",
            new_callable=AsyncMock,
        ) as mock_revoke:
            resp = await client.post(
                _ENDPOINT,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-PathForge-Signature": sig,
                },
            )

        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == user_id
        assert data["revoked_count"] == 2
        assert mock_revoke.call_count == 2

    async def test_registry_purged_after_blacklisting(
        self,
        client: AsyncClient,
        sso_secret: str,
        fake_redis: Any,
    ) -> None:
        """Session registry entries must be removed after blacklisting."""
        from app.core.sessions import _user_set_key

        user_id = str(uuid.uuid4())
        jti = str(uuid.uuid4())
        await _seed_session(fake_redis, user_id, jti)

        body = _body(user_id=user_id)
        sig = _sign(sso_secret, body)

        with patch(
            "app.core.token_blacklist.token_blacklist.revoke",
            new_callable=AsyncMock,
        ):
            await client.post(
                _ENDPOINT,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-PathForge-Signature": sig,
                },
            )

        remaining = await fake_redis.smembers(_user_set_key(user_id))
        assert remaining == set()

    async def test_response_shape(
        self,
        client: AsyncClient,
        sso_secret: str,
        fake_redis: Any,
    ) -> None:
        user_id = str(uuid.uuid4())
        await _seed_session(fake_redis, user_id, str(uuid.uuid4()))

        body = _body(user_id=user_id)
        sig = _sign(sso_secret, body)

        with patch(
            "app.core.token_blacklist.token_blacklist.revoke",
            new_callable=AsyncMock,
        ):
            resp = await client.post(
                _ENDPOINT,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-PathForge-Signature": sig,
                },
            )

        data = resp.json()
        assert set(data.keys()) == {"revoked_count", "user_id"}
        assert data["user_id"] == user_id


# ── 4. No-op for user with no sessions ───────────────────────────────


class TestNoSessions:
    async def test_returns_zero_when_no_active_sessions(
        self,
        client: AsyncClient,
        sso_secret: str,
        fake_redis: Any,
    ) -> None:
        body = _body(user_id=str(uuid.uuid4()))
        sig = _sign(sso_secret, body)
        resp = await client.post(
            _ENDPOINT,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-PathForge-Signature": sig,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["revoked_count"] == 0


# ── 5. Redis unavailability ───────────────────────────────────────────


class TestRedisUnavailability:
    async def test_503_when_list_for_user_raises(
        self,
        client: AsyncClient,
        sso_secret: str,
    ) -> None:
        body = _body()
        sig = _sign(sso_secret, body)

        with patch(
            "app.core.sessions.SessionRegistry.list_for_user",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis down"),
        ):
            resp = await client.post(
                _ENDPOINT,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-PathForge-Signature": sig,
                },
            )
        assert resp.status_code == 503


# ── 6. Partial blacklist failures ────────────────────────────────────


class TestPartialBlacklistFailures:
    async def test_503_when_all_blacklist_writes_fail(
        self,
        client: AsyncClient,
        sso_secret: str,
        fake_redis: Any,
    ) -> None:
        user_id = str(uuid.uuid4())
        await _seed_session(fake_redis, user_id, str(uuid.uuid4()))

        body = _body(user_id=user_id)
        sig = _sign(sso_secret, body)

        with patch(
            "app.core.token_blacklist.token_blacklist.revoke",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Blacklist Redis down"),
        ):
            resp = await client.post(
                _ENDPOINT,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-PathForge-Signature": sig,
                },
            )
        assert resp.status_code == 503

    async def test_partial_failure_returns_successful_count(
        self,
        client: AsyncClient,
        sso_secret: str,
        fake_redis: Any,
    ) -> None:
        """If one of two blacklist writes fails, revoked_count = 1."""
        user_id = str(uuid.uuid4())
        jti_ok = str(uuid.uuid4())
        jti_fail = str(uuid.uuid4())
        await _seed_session(fake_redis, user_id, jti_ok)
        await _seed_session(fake_redis, user_id, jti_fail)

        body = _body(user_id=user_id)
        sig = _sign(sso_secret, body)

        call_count = 0

        async def _flaky_revoke(_jti: str, **_kwargs: object) -> None:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("intermittent failure")

        with patch(
            "app.core.token_blacklist.token_blacklist.revoke",
            side_effect=_flaky_revoke,
        ):
            resp = await client.post(
                _ENDPOINT,
                content=body,
                headers={
                    "Content-Type": "application/json",
                    "X-PathForge-Signature": sig,
                },
            )

        assert resp.status_code == 200
        assert resp.json()["revoked_count"] == 1


# ── 7. _verify_signature unit tests (pure, sync) ─────────────────────


class TestVerifySignature:
    def test_valid_signature_returns_true(self) -> None:
        from app.core.sso_session_revoke import _verify_signature

        secret = "test-secret"
        body = b'{"user_id": "abc"}'
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
        assert _verify_signature(secret, body, sig) is True

    def test_wrong_signature_returns_false(self) -> None:
        from app.core.sso_session_revoke import _verify_signature

        assert _verify_signature("secret", b"body", "wrongsig") is False

    def test_empty_secret_returns_false(self) -> None:
        from app.core.sso_session_revoke import _verify_signature

        assert _verify_signature("", b"body", "anysig") is False

    def test_empty_header_returns_false(self) -> None:
        from app.core.sso_session_revoke import _verify_signature

        assert _verify_signature("secret", b"body", "") is False

    def test_tampered_body_returns_false(self) -> None:
        from app.core.sso_session_revoke import _verify_signature

        secret = "test-secret"
        original = b'{"user_id": "abc"}'
        sig = hmac.new(secret.encode(), original, hashlib.sha256).hexdigest()
        tampered = b'{"user_id": "evil"}'
        assert _verify_signature(secret, tampered, sig) is False
