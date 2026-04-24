"""
PathForge — User Service
==========================
Business logic for user registration, authentication, and profile management.
Separates domain logic from route handlers for testability and reuse.
"""

import hashlib
import logging
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy import update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.user import User
from app.schemas.user import TokenResponse
from app.services.email_service import EmailService, generate_token
from app.services.user_service_errors import (
    ExpiredResetTokenError,
    InactiveAccountError,
    InvalidCredentialsError,
    InvalidResetTokenError,
    OAuthOnlyAccountError,
    ResetTokenAlreadyUsedError,
    UnverifiedAccountError,
)

logger = logging.getLogger(__name__)


def _to_aware_utc(value: datetime) -> datetime:
    """Normalise a possibly-naive timestamp to a tz-aware UTC datetime.

    SQLite (used in tests) silently strips ``tzinfo`` even when the
    column is declared ``DateTime(timezone=True)``. PostgreSQL
    preserves it. To compare loaded timestamps with ``datetime.now(UTC)``
    we coerce naive values to UTC; aware values are returned unchanged.
    """
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


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
            InvalidCredentialsError: Email not found or password
                mismatch. Maps to HTTP 401 in the route handler.
            OAuthOnlyAccountError: Account has no password because it
                was provisioned via Google/Microsoft sign-in. The route
                handler returns HTTP 403 so callers can show the correct
                brand button.
            InactiveAccountError: ``is_active`` is False (admin-disabled
                or GDPR-deleted). Maps to HTTP 403.
            UnverifiedAccountError: Email-based account hasn't confirmed
                its email. Maps to HTTP 403 with a recovery message that
                points at the verification flow.

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
            raise InvalidCredentialsError

        # F23: Guard against OAuth users attempting password login.
        if user.hashed_password is None:
            raise OAuthOnlyAccountError(provider=user.auth_provider)

        if not verify_password(password, user.hashed_password):
            raise InvalidCredentialsError

        if not user.is_active:
            raise InactiveAccountError

        # F28 audit fix: enforce email verification for email-based
        # (non-OAuth) accounts before issuing tokens. Prior to this check
        # a user who registered but never clicked the verification link
        # could still log in and bypass the verification gate entirely.
        if not user.is_verified:
            raise UnverifiedAccountError

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

    # ── Password Reset (F30 atomic consumption) ───────────────────────

    @staticmethod
    async def reset_password_with_token(
        db: AsyncSession,
        *,
        token: str,
        new_password: str,
    ) -> None:
        """Validate the reset token and atomically swap the password.

        Raises one of:
            ``InvalidResetTokenError``     — token absent/unknown.
            ``ExpiredResetTokenError``    — token aged past TTL.
            ``ResetTokenAlreadyUsedError`` — concurrent caller won the
                                             atomic UPDATE first.

        See ``app.api.v1.auth.reset_password`` for the original audit
        finding (F30) and the concurrency rationale.
        """
        incoming_hash = hashlib.sha256(token.encode()).hexdigest()
        lookup = await db.execute(
            select(User).where(User.password_reset_token == incoming_hash)
        )
        user = lookup.scalar_one_or_none()
        if user is None:
            raise InvalidResetTokenError

        if user.password_reset_sent_at is None:
            # Missing timestamp → unrecoverable; scrub the token.
            user.password_reset_token = None
            await db.flush()
            raise InvalidResetTokenError

        sent_at = _to_aware_utc(user.password_reset_sent_at)
        expiry = sent_at + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        if datetime.now(UTC) > expiry:
            user.password_reset_token = None
            user.password_reset_sent_at = None
            await db.flush()
            raise ExpiredResetTokenError

        now = datetime.now(UTC)
        update_stmt = (
            sql_update(User)
            .where(
                User.id == user.id,
                User.password_reset_token == incoming_hash,
            )
            .values(
                hashed_password=hash_password(new_password),
                password_reset_token=None,
                password_reset_sent_at=None,
                # Sprint 41 C2: invalidate every existing session
                # after a password reset.
                tokens_invalidated_at=now,
            )
        )
        result = await db.execute(update_stmt)
        await db.flush()

        # mypy stub for ``Result`` doesn't declare ``rowcount``, but
        # the runtime ``CursorResult`` always provides it for DML.
        if result.rowcount == 0:  # type: ignore[attr-defined]
            logger.warning(
                "Reset token already consumed (race or replay): user_id=%s",
                user.id,
            )
            raise ResetTokenAlreadyUsedError

    # ── Resend Verification (F32 cooldown) ────────────────────────────

    @staticmethod
    async def resend_verification_if_eligible(
        db: AsyncSession,
        *,
        email: str,
    ) -> bool:
        """Issue a fresh verification email subject to per-account cooldown.

        Returns True when a verification mail was dispatched, False
        otherwise. Callers should treat both outcomes identically in
        responses to preserve anti-enumeration semantics.

        Eligibility:
            - account exists, ``is_active`` and not yet ``is_verified``
            - the last ``verification_sent_at`` is older than
              ``EMAIL_RESEND_COOLDOWN_SECONDS`` (or absent)
        """
        user = await UserService.get_by_email(db, email)
        if user is None or not user.is_active or user.is_verified:
            return False

        cooldown = timedelta(seconds=settings.email_resend_cooldown_seconds)
        now = datetime.now(UTC)
        last_sent = user.verification_sent_at

        if last_sent is not None:
            elapsed = now - _to_aware_utc(last_sent)
            if elapsed < cooldown:
                logger.info(
                    "Resend-verification suppressed by cooldown: "
                    "user_id=%s, seconds_remaining=%d",
                    user.id,
                    int((cooldown - elapsed).total_seconds()),
                )
                return False

        raw_token, hashed_token = generate_token()
        user.verification_token = hashed_token
        user.verification_sent_at = now
        await db.flush()

        EmailService.send_verification_email(
            to=user.email,
            token=raw_token,
            name=user.full_name,
        )
        return True
