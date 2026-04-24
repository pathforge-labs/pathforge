"""
PathForge API — Auth Routes
=============================
Registration, login, token refresh, logout, password reset, and email verification.
"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    oauth2_scheme,
)
from app.core.token_blacklist import token_blacklist
from app.models.user import User

logger = logging.getLogger(__name__)
from app.schemas.user import (
    ForgotPasswordRequest,
    LogoutRequest,
    MessageResponse,
    RefreshTokenRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    VerifyEmailRequest,
)
from app.services.email_service import EmailService, generate_token
from app.services.user_service import UserService
from app.services.user_service_errors import (
    InactiveAccountError,
    InvalidCredentialsError,
    OAuthOnlyAccountError,
    UnverifiedAccountError,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
@limiter.limit(settings.rate_limit_register)
async def register(
    request: Request,
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    # D6: Verify Turnstile CAPTCHA before creating user
    from app.core.turnstile import verify_turnstile_token
    await verify_turnstile_token(payload.turnstile_token)

    try:
        user = await UserService.create_user(
            db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )

        # F28: Send verification email instead of auto-login
        raw_token, hashed_token = generate_token()
        user.verification_token = hashed_token
        user.verification_sent_at = datetime.now(UTC)
        await db.flush()

        EmailService.send_verification_email(
            to=user.email,
            token=raw_token,
            name=user.full_name,
        )

        return user
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive access + refresh tokens",
)
@limiter.limit(settings.rate_limit_login)
async def login(
    request: Request,
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        return await UserService.authenticate(
            db, email=payload.email, password=payload.password
        )
    except InvalidCredentialsError as exc:
        # Credential failure — wrong email or wrong password. Kept at
        # 401 and surfaced with a deliberately generic message so the
        # response doesn't leak whether the email exists.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=exc.message,
        ) from exc
    except (
        InactiveAccountError,
        UnverifiedAccountError,
        OAuthOnlyAccountError,
    ) as exc:
        # Account-state rejections: credentials are technically valid,
        # but this login path is not allowed for this account. 403 is
        # semantically more accurate than 401 and lets clients (and
        # our tests) branch on status code + structured exception type
        # rather than matching on the detail string.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=exc.message,
        ) from exc


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an expired access token",
)
@limiter.limit(settings.rate_limit_refresh)
async def refresh_token(
    request: Request,
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    try:
        token_data = jwt.decode(
            payload.refresh_token,
            settings.jwt_refresh_secret,
            algorithms=[settings.jwt_algorithm],
        )
        user_id = token_data.get("sub")
        token_type = token_data.get("type")
        if user_id is None or token_type != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )
    except PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        ) from exc

    # Sprint 41 P1-2: Extract JTI for rotation + replay detection
    old_jti: str | None = token_data.get("jti")
    old_exp: int | None = token_data.get("exp")

    # Atomic rotation: consume_once checks AND revokes in a single Redis SETNX
    # (eliminates TOCTOU race window between separate check + revoke calls)
    if old_jti and old_exp:
        remaining = max(int(old_exp - datetime.now(UTC).timestamp()), 1)
        try:
            is_first_use = await token_blacklist.consume_once(old_jti, ttl_seconds=remaining)
            if not is_first_use:
                logger.warning("Refresh token replay detected for user %s", user_id)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Refresh token has already been used",
                )
        except HTTPException:
            raise
        except Exception:
            # Respect configurable fail mode (same as get_current_user)
            if settings.token_blacklist_fail_mode == "closed":
                logger.error("Refresh rotation failed — rejecting (fail-closed)")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service temporarily unavailable",
                ) from None
            logger.warning("Refresh rotation failed — allowing (fail-open)")

    user = await UserService.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    new_tokens = TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )

    return new_tokens


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke current access token and optional refresh token",
)
@limiter.limit(settings.rate_limit_logout)
async def logout(
    request: Request,
    payload: LogoutRequest | None = None,
    token: str = Depends(oauth2_scheme),
    _current_user: User = Depends(get_current_user),
) -> None:
    """Blacklist the current access token and optional refresh token."""
    # Revoke access token
    try:
        decoded = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        jti: str | None = decoded.get("jti")
        exp: int | None = decoded.get("exp")

        if jti and exp:
            remaining = max(int(exp - datetime.now(UTC).timestamp()), 1)
            await token_blacklist.revoke(jti, ttl_seconds=remaining)
    except PyJWTError:
        pass  # Token already invalid — nothing to revoke

    # Sprint 41 P1: Also revoke refresh token if provided
    if payload and payload.refresh_token:
        try:
            refresh_data = jwt.decode(
                payload.refresh_token,
                settings.jwt_refresh_secret,
                algorithms=[settings.jwt_algorithm],
            )
            refresh_jti: str | None = refresh_data.get("jti")
            refresh_exp: int | None = refresh_data.get("exp")
            if refresh_jti and refresh_exp:
                remaining_r = max(int(refresh_exp - datetime.now(UTC).timestamp()), 1)
                await token_blacklist.revoke(refresh_jti, ttl_seconds=remaining_r)
        except (PyJWTError, ConnectionError, OSError):
            pass  # Best-effort: JWT decode failure or Redis unavailability


# ── Sprint 39: Password Reset ──────────────────────────────────


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Request a password reset email",
)
@limiter.limit(settings.rate_limit_forgot_password)
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Send password reset email. Always returns 200 to prevent email enumeration."""
    user = await UserService.get_by_email(db, payload.email)

    if user and user.is_active:
        # Generate token pair (raw for email, hash for DB)
        raw_token, hashed_token = generate_token()
        user.password_reset_token = hashed_token
        user.password_reset_sent_at = datetime.now(UTC)
        await db.flush()

        EmailService.send_password_reset_email(
            to=user.email,
            token=raw_token,
            name=user.full_name,
        )

    # Always return success — never reveal whether email exists
    return MessageResponse(
        message="If an account with that email exists, a password reset link has been sent."
    )


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Reset password using a valid reset token",
)
@limiter.limit(settings.rate_limit_reset_password)
async def reset_password(
    request: Request,
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Validate reset token and update the user's password atomically.

    Concurrency model (Sprint 39 audit F30):
        The prior implementation did SELECT → check expiry → UPDATE as
        three separate steps. Two concurrent workers could both pass
        the SELECT+expiry phase against the same token, each then
        running an unconditional UPDATE. The row-level lock serialises
        the UPDATEs, but "last write wins" means an attacker who knew
        the token could overwrite the legitimate user's new password
        if they raced.

        The fix is a single atomic UPDATE gated on the token value:
        once the first writer clears ``password_reset_token``, any
        subsequent UPDATE filtering on ``password_reset_token = :hash``
        affects zero rows — we detect that via ``rowcount`` and reject
        the second caller. No database trip happens between the token
        check and the credential swap; consumption is truly one-shot.
    """
    incoming_hash = hashlib.sha256(payload.token.encode()).hexdigest()

    # Look up the token to validate existence + expiry *before* we
    # attempt the atomic swap. If the token is absent or expired we
    # return a distinct error, same as the legacy behaviour.
    lookup = await db.execute(
        select(User).where(User.password_reset_token == incoming_hash)
    )
    user = lookup.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    if not user.password_reset_sent_at:
        # Missing timestamp — scrub the token to prevent indefinite
        # retries and surface the generic "invalid/expired" error.
        user.password_reset_token = None
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    expiry = user.password_reset_sent_at + timedelta(
        minutes=settings.password_reset_token_expire_minutes
    )
    if datetime.now(UTC) > expiry:
        user.password_reset_token = None
        user.password_reset_sent_at = None
        await db.flush()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one.",
        )

    # Atomic consume-and-update: the WHERE clause requires the token
    # to still be present, so the second concurrent call sees
    # rowcount == 0 and is rejected as "already consumed".
    from sqlalchemy import update as sql_update

    now = datetime.now(UTC)
    update_stmt = (
        sql_update(User)
        .where(
            User.id == user.id,
            User.password_reset_token == incoming_hash,
        )
        .values(
            hashed_password=hash_password(payload.new_password),
            password_reset_token=None,
            password_reset_sent_at=None,
            # Sprint 41 C2: invalidate every existing session after a
            # password reset — a compromised refresh token must not
            # survive the rotation.
            tokens_invalidated_at=now,
        )
    )
    result = await db.execute(update_stmt)
    await db.flush()

    # mypy's stub for ``AsyncSession.execute`` returns ``Result[Any]``
    # which doesn't declare ``rowcount``, but SQLAlchemy 2.x
    # guarantees the attribute on the ``CursorResult`` returned by
    # DML statements. Ignoring the attr-defined lint here is the
    # idiomatic escape hatch; the runtime contract is documented at
    # https://docs.sqlalchemy.org/en/20/core/connections.html#sqlalchemy.engine.CursorResult.rowcount
    if result.rowcount == 0:  # type: ignore[attr-defined]
        # Another request (legitimate second click, or a racing
        # attacker) already consumed this token. Surface a distinct
        # message so the UI can point the user at /forgot-password
        # without implying an application bug.
        logger.warning(
            "Reset token already consumed (race or replay): user_id=%s",
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has already been used. Please request a new one.",
        )

    return MessageResponse(message="Password has been reset successfully.")


# ── Sprint 39: Email Verification ──────────────────────────────


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Verify email address using a verification token",
)
@limiter.limit(settings.rate_limit_verify_email)
async def verify_email(
    request: Request,
    payload: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Validate verification token and mark user as verified."""
    incoming_hash = hashlib.sha256(payload.token.encode()).hexdigest()

    result = await db.execute(
        select(User).where(User.verification_token == incoming_hash)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    # Check token expiry
    if user.verification_sent_at:
        expiry = user.verification_sent_at + timedelta(
            hours=settings.email_verification_token_expire_hours
        )
        if datetime.now(UTC) > expiry:
            user.verification_token = None
            user.verification_sent_at = None
            await db.flush()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Verification token has expired. Please request a new one.",
            )

    # Mark user as verified and clear token
    user.is_verified = True
    user.verification_token = None
    user.verification_sent_at = None
    await db.flush()

    # Send welcome email
    EmailService.send_welcome_email(to=user.email, name=user.full_name)

    return MessageResponse(message="Email verified successfully. Welcome to PathForge!")


@router.post(
    "/resend-verification",
    response_model=MessageResponse,
    summary="Resend email verification link",
)
@limiter.limit(settings.rate_limit_resend_verification)
async def resend_verification(
    request: Request,
    payload: ForgotPasswordRequest,  # Reuse: just needs email
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    """Resend verification email.

    Always returns 200 regardless of whether the account exists — this
    is deliberate anti-enumeration behaviour. The response text
    therefore must not distinguish "account not found", "already
    verified", "cooldown in effect", or "sent". The UI surfaces a
    generic "check your inbox" message; the user experience is
    identical in every branch.

    Abuse protection (Sprint 39 audit F32):
        slowapi's per-minute rate limit (``rate_limit_resend_verification``)
        throttles attacks at the *caller* level, but an attacker using
        many IPs or a legitimate user panic-clicking Resend could
        still generate dozens of verification mails per hour against
        a single address, burning our Resend daily quota (100/day on
        the free tier).

        We therefore enforce a per-*account* cooldown of
        ``EMAIL_RESEND_COOLDOWN_SECONDS`` — if the account's last
        ``verification_sent_at`` was within that window we silently
        short-circuit without calling the email provider. The caller
        still gets 200 + the generic message, so enumeration is
        preserved.
    """
    user = await UserService.get_by_email(db, payload.email)

    if user and user.is_active and not user.is_verified:
        cooldown = timedelta(seconds=settings.email_resend_cooldown_seconds)
        now = datetime.now(UTC)
        last_sent = user.verification_sent_at

        if last_sent is None or (now - last_sent) >= cooldown:
            raw_token, hashed_token = generate_token()
            user.verification_token = hashed_token
            user.verification_sent_at = now
            await db.flush()

            EmailService.send_verification_email(
                to=user.email,
                token=raw_token,
                name=user.full_name,
            )
        else:
            logger.info(
                "Resend-verification suppressed by cooldown: "
                "user_id=%s, seconds_remaining=%d",
                user.id,
                int((cooldown - (now - last_sent)).total_seconds()),
            )

    return MessageResponse(
        message="If an unverified account with that email exists, a verification link has been sent."
    )
