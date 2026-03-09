"""
PathForge API — Auth Routes
=============================
Registration, login, token refresh, logout, password reset, and email verification.
"""

import hashlib
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
from app.schemas.user import (
    ForgotPasswordRequest,
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
    except ValueError as exc:
        # Map inactive account to 403, bad credentials to 401
        detail = str(exc)
        if "inactive" in detail.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=detail,
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
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

    user = await UserService.get_by_id(db, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    return TokenResponse(
        access_token=create_access_token(str(user.id)),
        refresh_token=create_refresh_token(str(user.id)),
    )


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke current access token",
)
async def logout(
    token: str = Depends(oauth2_scheme),
    _current_user: User = Depends(get_current_user),
) -> None:
    """Blacklist the current access token so it cannot be reused."""
    try:
        payload = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        jti: str | None = payload.get("jti")
        exp: int | None = payload.get("exp")

        if jti and exp:
            remaining = max(int(exp - datetime.now(UTC).timestamp()), 1)
            await token_blacklist.revoke(jti, ttl_seconds=remaining)
    except PyJWTError:
        pass  # Token already invalid — nothing to revoke


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
        user.verification_token = hashed_token
        user.verification_sent_at = datetime.now(UTC)
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
    """Validate reset token and update the user's password."""
    # Find user with a matching token hash
    incoming_hash = hashlib.sha256(payload.token.encode()).hexdigest()

    result = await db.execute(
        select(User).where(User.verification_token == incoming_hash)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    # Check token expiry
    if user.verification_sent_at:
        expiry = user.verification_sent_at + timedelta(
            minutes=settings.password_reset_token_expire_minutes
        )
        if datetime.now(UTC) > expiry:
            # Clear expired token
            user.verification_token = None
            user.verification_sent_at = None
            await db.flush()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reset token has expired. Please request a new one.",
            )

    # Update password and clear token
    user.hashed_password = hash_password(payload.new_password)
    user.verification_token = None
    user.verification_sent_at = None
    await db.flush()

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
    """Resend verification email. Always returns 200 to prevent email enumeration."""
    user = await UserService.get_by_email(db, payload.email)

    if user and user.is_active and not user.is_verified:
        raw_token, hashed_token = generate_token()
        user.verification_token = hashed_token
        user.verification_sent_at = datetime.now(UTC)
        await db.flush()

        EmailService.send_verification_email(
            to=user.email,
            token=raw_token,
            name=user.full_name,
        )

    return MessageResponse(
        message="If an unverified account with that email exists, a verification link has been sent."
    )
