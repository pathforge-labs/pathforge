"""Tests for app.core.security module."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)
from app.models.user import User

pytestmark = pytest.mark.asyncio


def _make_request(cookies: dict[str, str] | None = None) -> Request:
    """Build a minimal Starlette Request fixture.

    Track 1 / ADR-0006: ``get_current_user`` now reads from the cookie
    jar in addition to the bearer header; tests that call it directly
    must provide a Request whose ``.cookies`` attribute returns the
    expected jar (empty by default — pure bearer-path tests).
    """
    request = MagicMock(spec=Request)
    request.cookies = cookies or {}
    return request


def test_hash_password_returns_string() -> None:
    hashed = hash_password("SomePass123!")
    assert isinstance(hashed, str)
    assert hashed != "SomePass123!"
    assert len(hashed) > 20


def test_hash_password_different_salts() -> None:
    """Each hash should use a unique salt and differ from prior hashes."""
    first = hash_password("SamePass123!")
    second = hash_password("SamePass123!")
    assert first != second


def test_verify_password_correct() -> None:
    hashed = hash_password("CorrectPass123!")
    assert verify_password("CorrectPass123!", hashed) is True


def test_verify_password_wrong() -> None:
    hashed = hash_password("CorrectPass123!")
    assert verify_password("WrongPass!", hashed) is False


def test_verify_password_empty_wrong() -> None:
    hashed = hash_password("NonEmpty123!")
    assert verify_password("", hashed) is False


def test_create_access_token_decodes_correctly() -> None:
    token = create_access_token("user-subject-123")
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == "user-subject-123"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "iat" in payload
    assert "exp" in payload


def test_create_access_token_custom_expiry() -> None:
    token = create_access_token("user-1", expires_delta=timedelta(minutes=5))
    payload = jwt.decode(
        token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
    )
    now_ts = datetime.now(UTC).timestamp()
    delta = payload["exp"] - now_ts
    assert 4 * 60 <= delta <= 6 * 60


def test_create_access_token_unique_jtis() -> None:
    """Each access token should contain a unique jti for revocation."""
    t1 = create_access_token("user-1")
    t2 = create_access_token("user-1")
    p1 = jwt.decode(t1, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    p2 = jwt.decode(t2, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert p1["jti"] != p2["jti"]


def test_create_refresh_token_type() -> None:
    token = create_refresh_token("user-1")
    payload = jwt.decode(
        token,
        settings.jwt_refresh_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["type"] == "refresh"
    assert payload["sub"] == "user-1"


def test_create_refresh_token_uses_refresh_secret() -> None:
    """Refresh tokens must be signed with jwt_refresh_secret, not jwt_secret."""
    token = create_refresh_token("user-1")
    with pytest.raises(jwt.InvalidSignatureError):
        jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
        )


def test_create_refresh_token_unique_jtis() -> None:
    t1 = create_refresh_token("user-1")
    t2 = create_refresh_token("user-1")
    p1 = jwt.decode(
        t1, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm],
    )
    p2 = jwt.decode(
        t2, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm],
    )
    assert p1["jti"] != p2["jti"]


async def _make_user(
    db_session: AsyncSession,
    *,
    email: str = "sec@pathforge.eu",
    is_active: bool = True,
    tokens_invalidated_at: datetime | None = None,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("SecTestPass123!"),
        full_name="Security Test",
        is_active=is_active,
        tokens_invalidated_at=tokens_invalidated_at,
    )
    db_session.add(user)
    await db_session.flush()
    await db_session.refresh(user)
    return user


async def test_get_current_user_valid_token(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    token = create_access_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await get_current_user(_make_request(), token=token, db=db_session)

    assert result.id == user.id
    assert result.email == user.email


async def test_get_current_user_expired_token(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="expired@pathforge.eu")
    token = create_access_token(
        str(user.id), expires_delta=timedelta(seconds=-10),
    )

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc:
        await get_current_user(_make_request(), token=token, db=db_session)

    assert exc.value.status_code == 401


async def test_get_current_user_revoked_token(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="revoked@pathforge.eu")
    token = create_access_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=True,
    ), pytest.raises(HTTPException) as exc:
        await get_current_user(_make_request(), token=token, db=db_session)

    assert exc.value.status_code == 401
    assert "revoked" in exc.value.detail.lower()


async def test_get_current_user_wrong_type(db_session: AsyncSession) -> None:
    """A refresh-type token must be rejected by the access dependency."""
    user = await _make_user(db_session, email="wrongtype@pathforge.eu")
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "type": "refresh",
        "jti": "some-jti",
    }
    token = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm,
    )

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc:
        await get_current_user(_make_request(), token=token, db=db_session)

    assert exc.value.status_code == 401


async def test_get_current_user_missing_sub(db_session: AsyncSession) -> None:
    now = datetime.now(UTC)
    payload = {
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "type": "access",
        "jti": "some-jti",
    }
    token = jwt.encode(
        payload, settings.jwt_secret, algorithm=settings.jwt_algorithm,
    )

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc:
        await get_current_user(_make_request(), token=token, db=db_session)

    assert exc.value.status_code == 401


async def test_get_current_user_invalid_signature(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="badsig@pathforge.eu")
    now = datetime.now(UTC)
    payload = {
        "sub": str(user.id),
        "iat": now,
        "exp": now + timedelta(minutes=5),
        "type": "access",
        "jti": "some-jti",
    }
    token = jwt.encode(
        payload, "totally-different-secret-32-bytes!", algorithm=settings.jwt_algorithm,
    )

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc:
        await get_current_user(_make_request(), token=token, db=db_session)

    assert exc.value.status_code == 401


async def test_get_current_user_malformed_token(db_session: AsyncSession) -> None:
    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc:
        await get_current_user(_make_request(), token="not-a-jwt-token", db=db_session)

    assert exc.value.status_code == 401


async def test_get_current_user_inactive_user(db_session: AsyncSession) -> None:
    user = await _make_user(
        db_session, email="inactive-sec@pathforge.eu", is_active=False,
    )
    token = create_access_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc:
        await get_current_user(_make_request(), token=token, db=db_session)

    assert exc.value.status_code == 403


async def test_get_current_user_user_not_found(db_session: AsyncSession) -> None:
    """A valid token whose subject is not in the DB must 401."""
    import uuid as _uuid

    token = create_access_token(str(_uuid.uuid4()))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc:
        await get_current_user(_make_request(), token=token, db=db_session)

    assert exc.value.status_code == 401


async def test_get_current_user_invalidated_token(
    db_session: AsyncSession,
) -> None:
    """Tokens issued before tokens_invalidated_at must be rejected."""
    future = datetime.now(UTC) + timedelta(days=365)
    user = await _make_user(
        db_session,
        email="invalidated@pathforge.eu",
        tokens_invalidated_at=future,
    )
    token = create_access_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc:
        await get_current_user(_make_request(), token=token, db=db_session)

    assert exc.value.status_code == 401
    assert "invalidated" in exc.value.detail.lower()


async def test_get_current_user_invalidated_before_issue(
    db_session: AsyncSession,
) -> None:
    """If tokens_invalidated_at is in the past relative to iat, token is valid."""
    past = datetime.now(UTC) - timedelta(hours=1)
    user = await _make_user(
        db_session,
        email="past-invalidated@pathforge.eu",
        tokens_invalidated_at=past,
    )
    token = create_access_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await get_current_user(_make_request(), token=token, db=db_session)

    assert result.id == user.id
