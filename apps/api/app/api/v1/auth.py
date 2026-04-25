"""
PathForge API — Auth Routes
=============================
Registration, login, token refresh, logout, password reset, and email verification.
"""

import hashlib
import logging
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.csrf import csrf_protect
from app.core.database import get_db
from app.core.rate_limit import limiter
from app.core.security import (
    clear_auth_cookies,
    create_access_token,
    create_refresh_token,
    get_current_user,
    oauth2_scheme,
    set_auth_cookies,
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
from app.services.user_service import UserService, _to_aware_utc
from app.services.user_service_errors import (
    DuplicateEmailError,
    InactiveAccountError,
    InvalidCredentialsError,
    OAuthOnlyAccountError,
    PasswordResetError,
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
    except DuplicateEmailError as exc:
        # Sprint 39 audit A-M1: typed exception (not stringly ValueError)
        # so the route handler doesn't have to interpret the message.
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=exc.message,
        ) from exc


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate and receive access + refresh tokens",
)
@limiter.limit(settings.rate_limit_login)
async def login(
    request: Request,
    response: Response,
    payload: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Authenticate and return tokens.

    Track 1 / ADR-0006: tokens are returned in *both* the JSON body
    (legacy clients) and as `httpOnly` cookies (cookie-first clients).
    Returning both during the migration window means a client can pick
    its path with no server-side feature flag.
    """
    try:
        tokens = await UserService.authenticate(
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

    set_auth_cookies(
        response,
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
    )
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh an expired access token",
)
@limiter.limit(settings.rate_limit_refresh)
async def refresh_token(
    request: Request,
    response: Response,
    payload: RefreshTokenRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """Rotate the refresh + access token pair.

    Track 1 / ADR-0006: the refresh token is accepted from *either* the
    `pathforge_refresh` cookie (cookie-first path) or the JSON body
    (legacy path). Body wins if both are present so an explicit client
    request is always honoured. Empty / missing → 401.
    """
    # Cookie-first; body falls back. Body has precedence on conflict so
    # a client that explicitly passes a token is never overridden by a
    # stale cookie.
    body_token = payload.refresh_token if payload else None
    cookie_token = request.cookies.get("pathforge_refresh") or None
    refresh_input = body_token or cookie_token
    if not refresh_input:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
        )

    try:
        token_data = jwt.decode(
            refresh_input,
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
    set_auth_cookies(
        response,
        access_token=new_tokens.access_token,
        refresh_token=new_tokens.refresh_token,
    )
    return new_tokens


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke current access token and optional refresh token",
    dependencies=[Depends(csrf_protect)],
)
@limiter.limit(settings.rate_limit_logout)
async def logout(
    request: Request,
    response: Response,
    payload: LogoutRequest | None = None,
    token: str | None = Depends(oauth2_scheme),
    _current_user: User = Depends(get_current_user),
) -> None:
    """Blacklist the current access token and optional refresh token.

    Redis failure handling (Sprint 39 audit S-M3):
        Logout MUST revoke the token to honour the user's intent.
        If the blacklist (Redis) is unavailable, fail-mode policy
        decides what to do:
        - ``token_blacklist_fail_mode == "closed"`` (production
          default): refuse the logout with 503 — the token stays
          live, but the caller is told. Better than silently
          succeeding while the session continues.
        - ``"open"``: log a warning and return 204 — degraded UX
          but tolerable in dev.
        Previously the OS/connection error branch was swallowed
        with ``pass`` regardless of mode.
    """
    revoke_errors: list[Exception] = []

    # Track 1 / ADR-0006: token may arrive via cookie, header, or both.
    # Prefer header (oauth2_scheme) when present so an explicit caller's
    # intent is honoured; fall back to cookie for cookie-first clients.
    cookie_access = request.cookies.get("pathforge_access") or None
    access_token = token or cookie_access

    # Revoke access token
    if access_token:
        try:
            decoded = jwt.decode(
                access_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
            )
            jti: str | None = decoded.get("jti")
            exp: int | None = decoded.get("exp")

            if jti and exp:
                remaining = max(int(exp - datetime.now(UTC).timestamp()), 1)
                try:
                    await token_blacklist.revoke(jti, ttl_seconds=remaining)
                except (ConnectionError, OSError) as exc:
                    revoke_errors.append(exc)
        except PyJWTError:
            pass  # Token already invalid — nothing to revoke

    # Sprint 41 P1: Also revoke refresh token if provided.
    # Track 1 / ADR-0006: refresh from cookie also revoked.
    cookie_refresh = request.cookies.get("pathforge_refresh") or None
    refresh_token_to_revoke = (
        payload.refresh_token if payload and payload.refresh_token else cookie_refresh
    )
    if refresh_token_to_revoke:
        try:
            refresh_data = jwt.decode(
                refresh_token_to_revoke,
                settings.jwt_refresh_secret,
                algorithms=[settings.jwt_algorithm],
            )
            refresh_jti: str | None = refresh_data.get("jti")
            refresh_exp: int | None = refresh_data.get("exp")
            if refresh_jti and refresh_exp:
                remaining_r = max(int(refresh_exp - datetime.now(UTC).timestamp()), 1)
                try:
                    await token_blacklist.revoke(refresh_jti, ttl_seconds=remaining_r)
                except (ConnectionError, OSError) as exc:
                    revoke_errors.append(exc)
        except PyJWTError:
            pass  # JWT decode failure — token already useless

    if revoke_errors:
        # Redis was unreachable for at least one token. Honour the
        # configured fail-mode (matches ``get_current_user`` semantics).
        if settings.token_blacklist_fail_mode == "closed":
            logger.error(
                "Logout: blacklist unavailable (%d revoke failure(s)) — "
                "rejecting logout in fail-closed mode",
                len(revoke_errors),
                exc_info=revoke_errors[0],
            )
            # Do NOT clear cookies here — the user's intent (logout)
            # was not honoured and the session is still live server-side.
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service temporarily unavailable",
            ) from revoke_errors[0]
        logger.warning(
            "Logout: blacklist unavailable (%d revoke failure(s)) — "
            "completing in fail-open mode (tokens may remain live)",
            len(revoke_errors),
            exc_info=revoke_errors[0],
        )

    # Track 1 / ADR-0006: clear auth cookies on successful logout (or
    # fail-open path). The client is told the session is dead even if
    # Redis-side revocation degraded.
    clear_auth_cookies(response)


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
    # Sprint 39 audit S-M4: Turnstile gate (no-op when secret not set).
    from app.core.turnstile import verify_turnstile_token
    await verify_turnstile_token(payload.turnstile_token)

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
    """Thin orchestrator around ``UserService.reset_password_with_token``.

    The service performs the full validate-and-swap flow atomically;
    each failure mode raises a distinct ``PasswordResetError``
    subclass that we surface as 400 with the exception's user-facing
    ``message``. See the service docstring for the F30 concurrency
    rationale.
    """
    try:
        await UserService.reset_password_with_token(
            db, token=payload.token, new_password=payload.new_password,
        )
    except PasswordResetError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=exc.message,
        ) from exc

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
        # SQLite drops tzinfo even with DateTime(timezone=True). Coerce to
        # aware-UTC so the comparison with datetime.now(UTC) below is valid
        # under both Postgres (prod) and SQLite (tests).
        expiry = _to_aware_utc(user.verification_sent_at) + timedelta(
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

    Thin orchestrator around
    ``UserService.resend_verification_if_eligible``. Eligibility
    (account exists, active, unverified, outside cooldown) and the
    email dispatch itself live in the service — see the F32 audit
    rationale there. The response intentionally does not distinguish
    eligible/ineligible cases to preserve anti-enumeration semantics.
    """
    await UserService.resend_verification_if_eligible(db, email=payload.email)
    return MessageResponse(
        message=(
            "If an unverified account with that email exists, "
            "a verification link has been sent."
        )
    )
