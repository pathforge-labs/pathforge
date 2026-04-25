"""Unit tests for UserService — direct DB session, covers all branches."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from app.services.user_service import UserService
from app.services.user_service_errors import (
    DuplicateEmailError,
    InactiveAccountError,
    InvalidCredentialsError,
    OAuthOnlyAccountError,
    UnverifiedAccountError,
)

# ── create_user ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_user_email_success(db_session: Any) -> None:
    user = await UserService.create_user(
        db_session,
        email="newuser@example.com",
        password="SecurePass1!",
        full_name="New User",
    )
    assert user.email == "newuser@example.com"
    assert user.hashed_password is not None
    assert user.full_name == "New User"
    assert user.auth_provider == "email"
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_create_user_oauth_no_password(db_session: Any) -> None:
    user = await UserService.create_user(
        db_session,
        email="oauth@example.com",
        password=None,
        full_name="OAuth User",
        auth_provider="google",
        is_verified=True,
    )
    assert user.hashed_password is None
    assert user.auth_provider == "google"
    assert user.is_verified is True


@pytest.mark.asyncio
async def test_create_user_duplicate_email_raises(db_session: Any) -> None:
    await UserService.create_user(
        db_session,
        email="dup@example.com",
        password="pass",
        full_name="First",
    )
    with pytest.raises(DuplicateEmailError, match="already exists"):
        await UserService.create_user(
            db_session,
            email="dup@example.com",
            password="pass2",
            full_name="Second",
        )


# ── authenticate ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_authenticate_success(db_session: Any) -> None:
    await UserService.create_user(
        db_session,
        email="auth@example.com",
        password="MyP@ssw0rd",
        full_name="Auth User",
        is_verified=True,
    )
    token = await UserService.authenticate(
        db_session, email="auth@example.com", password="MyP@ssw0rd",
    )
    assert token.access_token
    assert token.refresh_token


@pytest.mark.asyncio
async def test_authenticate_user_not_found_raises(db_session: Any) -> None:
    with pytest.raises(InvalidCredentialsError, match="Incorrect email or password"):
        await UserService.authenticate(
            db_session, email="nobody@example.com", password="pass",
        )


@pytest.mark.asyncio
async def test_authenticate_oauth_user_raises(db_session: Any) -> None:
    await UserService.create_user(
        db_session,
        email="google@example.com",
        password=None,
        full_name="OAuth",
        auth_provider="google",
        is_verified=True,
    )
    with pytest.raises(OAuthOnlyAccountError, match="google sign-in") as exc_info:
        await UserService.authenticate(
            db_session, email="google@example.com", password="anything",
        )
    # The exception carries the provider as a structured attribute so
    # the route layer can branch on it without parsing the message.
    assert exc_info.value.provider == "google"


@pytest.mark.asyncio
async def test_authenticate_wrong_password_raises(db_session: Any) -> None:
    await UserService.create_user(
        db_session,
        email="wrongpw@example.com",
        password="correct",
        full_name="User",
    )
    with pytest.raises(InvalidCredentialsError, match="Incorrect email or password"):
        await UserService.authenticate(
            db_session, email="wrongpw@example.com", password="wrong",
        )


@pytest.mark.asyncio
async def test_authenticate_inactive_user_raises(db_session: Any) -> None:
    user = await UserService.create_user(
        db_session,
        email="inactive@example.com",
        password="pass123",
        full_name="Inactive",
        is_verified=True,
    )
    user.is_active = False
    await db_session.flush()

    with pytest.raises(InactiveAccountError, match="inactive"):
        await UserService.authenticate(
            db_session, email="inactive@example.com", password="pass123",
        )


@pytest.mark.asyncio
@pytest.mark.no_auto_verify
async def test_authenticate_unverified_user_raises(db_session: Any) -> None:
    """Email-based accounts must verify before they can log in (F28 audit).

    Sanity check against regression: prior to this enforcement an
    unverified user could sign up and immediately log in, bypassing the
    verification flow entirely.
    """
    await UserService.create_user(
        db_session,
        email="unverified@example.com",
        password="pass123",
        full_name="Unverified",
        # is_verified defaults to False for email-based users
    )

    with pytest.raises(UnverifiedAccountError, match="verify your email"):
        await UserService.authenticate(
            db_session, email="unverified@example.com", password="pass123",
        )


@pytest.mark.asyncio
@pytest.mark.no_auto_verify
async def test_authenticate_unverified_user_rejected_before_token_issued(
    db_session: Any,
) -> None:
    """Verification gate blocks token issuance even if credentials are valid."""
    await UserService.create_user(
        db_session,
        email="gate@example.com",
        password="ValidPass1!",
        full_name="Gate",
    )

    # Correct password, but account is not verified — no tokens should be
    # returned and the caller should see a clear "verify email" message.
    with pytest.raises(UnverifiedAccountError) as exc_info:
        await UserService.authenticate(
            db_session, email="gate@example.com", password="ValidPass1!",
        )
    assert "verify your email" in exc_info.value.message.lower()


# ── get_by_id ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_id_found(db_session: Any) -> None:
    user = await UserService.create_user(
        db_session,
        email="byid@example.com",
        password="pass",
        full_name="ByID",
    )
    found = await UserService.get_by_id(db_session, user.id)
    assert found is not None
    assert found.email == "byid@example.com"


@pytest.mark.asyncio
async def test_get_by_id_string_uuid(db_session: Any) -> None:
    user = await UserService.create_user(
        db_session,
        email="byidstr@example.com",
        password="pass",
        full_name="ByIDStr",
    )
    found = await UserService.get_by_id(db_session, str(user.id))
    assert found is not None


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: Any) -> None:
    found = await UserService.get_by_id(db_session, uuid.uuid4())
    assert found is None


# ── get_by_email ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_email_found(db_session: Any) -> None:
    await UserService.create_user(
        db_session,
        email="byemail@example.com",
        password="pass",
        full_name="ByEmail",
    )
    found = await UserService.get_by_email(db_session, "byemail@example.com")
    assert found is not None
    assert found.email == "byemail@example.com"


@pytest.mark.asyncio
async def test_get_by_email_not_found(db_session: Any) -> None:
    found = await UserService.get_by_email(db_session, "notexist@example.com")
    assert found is None


# ── update_profile ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_update_profile_sets_non_none_values(db_session: Any) -> None:
    user = await UserService.create_user(
        db_session,
        email="update@example.com",
        password="pass",
        full_name="Original",
    )
    updated = await UserService.update_profile(
        db_session, user, full_name="Updated Name",
    )
    assert updated.full_name == "Updated Name"


@pytest.mark.asyncio
async def test_update_profile_skips_none_values(db_session: Any) -> None:
    user = await UserService.create_user(
        db_session,
        email="skipnone@example.com",
        password="pass",
        full_name="Keep This",
    )
    updated = await UserService.update_profile(
        db_session, user, full_name=None,
    )
    assert updated.full_name == "Keep This"
