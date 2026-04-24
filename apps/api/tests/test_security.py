"""
PathForge — Security Module Unit Tests
=========================================
Tests for password hashing, JWT token creation, and the
get_current_user FastAPI dependency (app/core/security.py).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import jwt
import pytest
from fastapi import HTTPException

from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
)

# ── hash_password / verify_password ──────────────────────────


def test_hash_password_returns_string() -> None:
    h = hash_password("Secret1!")
    assert isinstance(h, str)
    assert h != "Secret1!"


def test_verify_password_correct() -> None:
    h = hash_password("MyPass123")
    assert verify_password("MyPass123", h) is True


def test_verify_password_incorrect() -> None:
    h = hash_password("MyPass123")
    assert verify_password("wrong", h) is False


def test_hash_password_is_different_each_call() -> None:
    h1 = hash_password("Same")
    h2 = hash_password("Same")
    assert h1 != h2  # unique salts


# ── create_access_token ───────────────────────────────────────


def test_create_access_token_returns_string() -> None:
    token = create_access_token(subject="user-1")
    assert isinstance(token, str)
    assert len(token) > 10


def test_create_access_token_has_correct_claims() -> None:
    from app.core.config import settings

    token = create_access_token(subject="user-42")
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["sub"] == "user-42"
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload


def test_create_access_token_custom_expiry() -> None:
    from app.core.config import settings

    token = create_access_token(
        subject="user-99", expires_delta=timedelta(hours=2)
    )
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
    iat = datetime.fromtimestamp(payload["iat"], tz=UTC)
    diff = (exp - iat).total_seconds()
    assert abs(diff - 7200) < 5  # 2 hours ± 5 seconds


def test_create_access_token_unique_jtis() -> None:
    t1 = create_access_token("u1")
    t2 = create_access_token("u1")
    from app.core.config import settings

    p1 = jwt.decode(t1, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    p2 = jwt.decode(t2, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    assert p1["jti"] != p2["jti"]


# ── create_refresh_token ──────────────────────────────────────


def test_create_refresh_token_returns_string() -> None:
    token = create_refresh_token("user-5")
    assert isinstance(token, str)


def test_create_refresh_token_has_correct_type() -> None:
    from app.core.config import settings

    token = create_refresh_token("user-5")
    payload = jwt.decode(
        token,
        settings.jwt_refresh_secret,
        algorithms=[settings.jwt_algorithm],
    )
    assert payload["type"] == "refresh"
    assert payload["sub"] == "user-5"
    assert "jti" in payload


def test_create_refresh_token_longer_expiry_than_access() -> None:
    from app.core.config import settings

    access = create_access_token("u")
    refresh = create_refresh_token("u")

    ap = jwt.decode(access, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    rp = jwt.decode(
        refresh, settings.jwt_refresh_secret, algorithms=[settings.jwt_algorithm]
    )
    assert rp["exp"] > ap["exp"]


# ── get_current_user ──────────────────────────────────────────


def _make_valid_token(user_id: str) -> str:
    return create_access_token(subject=user_id)


@pytest.mark.asyncio
async def test_get_current_user_returns_user(db_session: Any) -> None:
    from app.models.user import User as UserModel

    user = UserModel(
        email=f"sec-test-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("Pass1!"),
        full_name="Sec Tester",
    )
    db_session.add(user)
    await db_session.flush()

    token = _make_valid_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ):
        result = await get_current_user(token=token, db=db_session)

    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_current_user_invalid_token(db_session: Any) -> None:
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token="not.a.valid.token", db=db_session)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_revoked_token(db_session: Any) -> None:
    from app.models.user import User as UserModel

    user = UserModel(
        email=f"revoked-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("Pass1!"),
        full_name="Revoked User",
    )
    db_session.add(user)
    await db_session.flush()

    token = _make_valid_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=True,
    ), pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401
    assert "revoked" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_inactive_user(db_session: Any) -> None:
    from app.models.user import User as UserModel

    user = UserModel(
        email=f"inactive-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("Pass1!"),
        full_name="Inactive User",
        is_active=False,
    )
    db_session.add(user)
    await db_session.flush()

    token = _make_valid_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_get_current_user_nonexistent_user(db_session: Any) -> None:
    token = _make_valid_token(str(uuid.uuid4()))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_blacklist_fail_open(db_session: Any) -> None:
    """When blacklist check raises (Redis down), fail-open allows the request."""
    from app.models.user import User as UserModel

    user = UserModel(
        email=f"failopen-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("Pass1!"),
        full_name="Fail Open User",
    )
    db_session.add(user)
    await db_session.flush()

    token = _make_valid_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        side_effect=ConnectionError("Redis down"),
    ):
        result = await get_current_user(token=token, db=db_session)

    assert result.id == user.id


@pytest.mark.asyncio
async def test_get_current_user_blacklist_fail_closed(db_session: Any) -> None:
    """In fail-closed mode, blacklist errors reject the request with 503."""
    from app.core.config import settings
    from app.models.user import User as UserModel

    user = UserModel(
        email=f"failclosed-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("Pass1!"),
        full_name="Fail Closed User",
    )
    db_session.add(user)
    await db_session.flush()

    token = _make_valid_token(str(user.id))

    original_mode = settings.token_blacklist_fail_mode
    object.__setattr__(settings, "token_blacklist_fail_mode", "closed")
    try:
        with patch(
            "app.core.token_blacklist.TokenBlacklist.is_revoked",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Redis down"),
        ), pytest.raises(HTTPException) as exc_info:
            await get_current_user(token=token, db=db_session)
        assert exc_info.value.status_code == 503
    finally:
        object.__setattr__(settings, "token_blacklist_fail_mode", original_mode)


@pytest.mark.asyncio
async def test_get_current_user_invalidated_token(db_session: Any) -> None:
    """Token issued before tokens_invalidated_at is rejected."""
    from app.models.user import User as UserModel

    user = UserModel(
        email=f"invalidated-{uuid.uuid4()}@example.com",
        hashed_password=hash_password("Pass1!"),
        full_name="Invalidated User",
        tokens_invalidated_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(user)
    await db_session.flush()

    token = _make_valid_token(str(user.id))

    with patch(
        "app.core.token_blacklist.TokenBlacklist.is_revoked",
        new_callable=AsyncMock,
        return_value=False,
    ), pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401
    assert "invalidated" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_get_current_user_wrong_token_type(db_session: Any) -> None:
    """Refresh tokens must not be accepted as access tokens."""
    token = create_refresh_token("user-x")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(token=token, db=db_session)
    assert exc_info.value.status_code == 401
