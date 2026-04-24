"""
PathForge — User Service
==========================
Business logic for user registration, authentication, and profile management.
Separates domain logic from route handlers for testability and reuse.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import TokenResponse


class UserService:
    """Encapsulates user-related business logic."""

    @staticmethod
    async def create_user(
        db: AsyncSession,
        *,
        email: str,
        password: str | None = None,
        full_name: str,
        auth_provider: str = "email",
        is_verified: bool = False,
    ) -> User:
        """Register a new user. Raises ValueError if email already taken.

        Args:
            password: Required for email users, None for OAuth users (F24).
            auth_provider: "email", "google", or "microsoft".
            is_verified: OAuth users are pre-verified; email users are not.
        """
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise ValueError("A user with this email already exists")

        user = User(
            email=email,
            hashed_password=hash_password(password) if password else None,
            full_name=full_name,
            auth_provider=auth_provider,
            is_verified=is_verified,
        )
        db.add(user)
        await db.flush()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate(
        db: AsyncSession,
        *,
        email: str,
        password: str,
    ) -> TokenResponse:
        """Authenticate a user and return access + refresh tokens.

        Raises:
            ValueError: If credentials are invalid, the account is inactive,
                or the email address has not been verified.

        Security note:
            The ``is_verified`` check is performed *after* password
            verification so that attackers cannot use login responses to
            enumerate which emails are registered but unverified (which
            would leak sign-up information). Unverified accounts see a
            distinct "verify your email" message instead of a generic
            credential error — this matches expected UX for the legitimate
            owner of the credentials while still preventing enumeration by
            unauthenticated callers.
        """
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError("Incorrect email or password")

        # F23: Guard against OAuth users attempting password login
        if user.hashed_password is None:
            raise ValueError(
                f"This account uses {user.auth_provider} sign-in. "
                f"Please use the {user.auth_provider} button to log in."
            )

        if not verify_password(password, user.hashed_password):
            raise ValueError("Incorrect email or password")

        if not user.is_active:
            raise ValueError("User account is inactive")

        # F28 audit fix: enforce email verification for email-based
        # (non-OAuth) accounts before issuing tokens. Prior to this check
        # a user who registered but never clicked the verification link
        # could still log in and bypass the verification gate entirely.
        if not user.is_verified:
            raise ValueError(
                "Please verify your email address before signing in. "
                "Check your inbox for the verification link "
                "or request a new one from the sign-in page."
            )

        return TokenResponse(
            access_token=create_access_token(str(user.id)),
            refresh_token=create_refresh_token(str(user.id)),
        )

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID | str) -> User | None:
        """Fetch a user by their UUID (accepts string for JWT subject)."""
        uid = uuid.UUID(user_id) if isinstance(user_id, str) else user_id
        result = await db.execute(select(User).where(User.id == uid))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> User | None:
        """Fetch a user by their email address."""
        result = await db.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        user: User,
        **fields: str | None,
    ) -> User:
        """Update a user's profile fields. Only sets non-None values."""
        for field, value in fields.items():
            if value is not None:
                setattr(user, field, value)
        await db.flush()
        await db.refresh(user)
        return user
