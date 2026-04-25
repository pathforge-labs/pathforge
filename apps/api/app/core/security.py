"""
PathForge API — Security & Authentication
==========================================
JWT token creation, password hashing, and auth dependencies.

Usage:
    from app.core.security import create_access_token, get_current_user
"""

from __future__ import annotations

import secrets
import uuid as _uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db

if TYPE_CHECKING:
    from app.models.user import User

# OAuth2 scheme is auto_error=False so we can fall back to the cookie path
# (Track 1, ADR-0006) without raising 401 on header-less requests when a
# cookie is present.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

# ── Cookie names (Track 1 / ADR-0006) ────────────────────────────────────────
# Single source of truth — used by the auth route, the dependency, and the
# logout helper. Names are deliberately product-prefixed so an httpOnly
# pathforge_access cookie is unambiguous in browser dev tools.
ACCESS_COOKIE_NAME = "pathforge_access"
REFRESH_COOKIE_NAME = "pathforge_refresh"
CSRF_COOKIE_NAME = "pathforge_csrf"
CSRF_HEADER_NAME = "x-csrf-token"


def _set_secure_cookie(
    response: Response,
    *,
    key: str,
    value: str,
    max_age: int,
    httponly: bool = True,
) -> None:
    """Apply the canonical Set-Cookie attributes for this app.

    `secure` and `samesite="strict"` are always set in production; in
    development the secure flag relaxes so cookies still work over the
    plaintext localhost dev loop. `domain` is left unset to bind cookies
    to the API host — cross-subdomain sharing is opt-in via config. The
    `httponly` flag is opt-out so the CSRF cookie can flip it without
    redefining every other attribute.
    """
    response.set_cookie(
        key=key,
        value=value,
        max_age=max_age,
        httponly=httponly,
        secure=settings.environment == "production",
        samesite="strict",
        path="/",
    )


def set_auth_cookies(
    response: Response, *, access_token: str, refresh_token: str
) -> str:
    """Set the auth cookie pair plus a fresh CSRF cookie.

    Returns the raw CSRF token so the caller can include it in the JSON
    body — clients that prefer the body-driven path don't need to read
    the cookie. The CSRF cookie itself is intentionally NOT httpOnly so
    JS can read it for the double-submit echo header.
    """
    _set_secure_cookie(
        response,
        key=ACCESS_COOKIE_NAME,
        value=access_token,
        max_age=settings.jwt_access_token_expire_minutes * 60,
    )
    _set_secure_cookie(
        response,
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
    )
    csrf_token = secrets.token_urlsafe(32)
    _set_secure_cookie(
        response,
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.jwt_refresh_token_expire_days * 24 * 60 * 60,
        httponly=False,  # readable by JS for double-submit echo
    )
    return csrf_token


def clear_auth_cookies(response: Response) -> None:
    """Delete the auth cookie pair and CSRF cookie on logout.

    The `httponly` flag must match the original Set-Cookie header so the
    browser correctly identifies which cookie to delete (Gemini review on
    PR #28). The CSRF cookie was set with `httponly=False`, so its
    deletion must also drop the flag — otherwise Chrome and Safari skip
    the deletion silently and the session lingers after logout.
    """
    secure = settings.environment == "production"
    for name in (ACCESS_COOKIE_NAME, REFRESH_COOKIE_NAME):
        response.delete_cookie(
            key=name,
            path="/",
            samesite="strict",
            secure=secure,
            httponly=True,
        )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        samesite="strict",
        secure=secure,
        httponly=False,
    )


def hash_password(password: str) -> str:
    """Hash a plain-text password using bcrypt.

    Uses 4 rounds in testing mode for performance (~60x faster).
    Production uses bcrypt default (12 rounds).
    """
    import os

    password_bytes = password.encode("utf-8")
    rounds = 4 if os.environ.get("ENVIRONMENT") == "testing" else 12
    salt = bcrypt.gensalt(rounds=rounds)
    return str(bcrypt.hashpw(password_bytes, salt).decode("utf-8"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a hashed password."""
    return bool(bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    ))


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token with unique jti for revocation."""
    expire = datetime.now(UTC) + (
        expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    now = datetime.now(UTC)
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "access",
        "jti": str(_uuid.uuid4()),
    }
    return str(jwt.encode(to_encode, settings.jwt_secret, algorithm=settings.jwt_algorithm))


def create_refresh_token(subject: str) -> str:
    """Create a JWT refresh token with longer expiry and unique jti."""
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.jwt_refresh_token_expire_days)
    to_encode = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "type": "refresh",
        "jti": str(_uuid.uuid4()),  # unique ID for token rotation/revocation
    }
    return str(jwt.encode(to_encode, settings.jwt_refresh_secret, algorithm=settings.jwt_algorithm))


async def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: extract and validate the current user from JWT token.

    Token resolution order (Track 1 / ADR-0006):
        1. ``pathforge_access`` httpOnly cookie (preferred — XSS-resistant).
        2. ``Authorization: Bearer <token>`` header (legacy fallback,
           sunsetted ``settings.auth_legacy_header_deprecated_after``
           days post-launch; emits a Sentry breadcrumb after that date).

    The fallback is intentional during the 30-day rollout window so
    in-flight clients with the old SDK keep working. After the deadline
    the breadcrumb makes residual usage observable.
    """
    import logging

    from app.core.token_blacklist import token_blacklist
    from app.models.user import User

    logger = logging.getLogger(__name__)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Cookie path first; header is the legacy fallback. Empty string
    # cookies are treated as missing so a stale `pathforge_access=` from
    # a half-cleared client doesn't pre-empt the header.
    cookie_token = request.cookies.get(ACCESS_COOKIE_NAME) or None
    auth_token = cookie_token or token
    auth_path = "cookie" if cookie_token else ("bearer" if token else None)

    if auth_token is None:
        raise credentials_exception

    try:
        payload = jwt.decode(
            auth_token, settings.jwt_secret, algorithms=[settings.jwt_algorithm],
        )
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        jti: str | None = payload.get("jti")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except PyJWTError as exc:
        raise credentials_exception from exc

    # Sentry telemetry: record which path each request used so we can
    # observe the cookie-rollout hitting ≥95 % within 30 days. Tagging
    # at this layer keeps the auth handler bodies free of telemetry
    # boilerplate.
    if auth_path == "bearer" and settings.auth_legacy_header_deprecated_after:
        deprecation_date = settings.auth_legacy_header_deprecated_after
        if datetime.now(UTC).date() >= deprecation_date:
            logger.warning(
                "Auth legacy bearer header used after deprecation date %s",
                deprecation_date.isoformat(),
            )

    # Check token blacklist (Sprint 40 Audit P1-1: configurable fail mode)
    if jti:
        try:
            if await token_blacklist.is_revoked(jti):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except HTTPException:
            raise
        except Exception:
            if settings.token_blacklist_fail_mode == "closed":
                logger.error("Token blacklist check failed — rejecting request (fail-closed mode)")
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Authentication service temporarily unavailable",
                ) from None
            logger.warning("Token blacklist check failed — allowing request (fail-open mode)")

    # Sprint 39 audit S-M5: a malformed ``sub`` claim (non-UUID) used
    # to surface as a 500 via the global handler. Treat it as a
    # credential failure — the token is shaped wrong, exactly the
    # scenario ``credentials_exception`` is for.
    try:
        user_uuid = _uuid.UUID(user_id)
    except (ValueError, AttributeError, TypeError) as exc:
        logger.warning("JWT 'sub' claim is not a valid UUID")
        raise credentials_exception from exc

    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription))
        .where(User.id == user_uuid)
    )
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account",
        )

    # Sprint 41: Reject tokens issued before a global invalidation event
    # (password reset, security lockout) — ensures all pre-existing sessions
    # are terminated after credential change.
    iat = payload.get("iat")
    if user.tokens_invalidated_at and iat and iat < user.tokens_invalidated_at.timestamp():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been invalidated. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
