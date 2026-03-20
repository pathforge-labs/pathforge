"""
PathForge API — Security & Authentication
==========================================
JWT token creation, password hashing, and auth dependencies.

Usage:
    from app.core.security import create_access_token, get_current_user
"""

from __future__ import annotations

import uuid as _uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import bcrypt
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import PyJWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db

if TYPE_CHECKING:
    from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


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
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency: extract and validate the current user from JWT token."""
    import logging

    from app.core.token_blacklist import token_blacklist
    from app.models.user import User

    logger = logging.getLogger(__name__)

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id: str | None = payload.get("sub")
        token_type: str | None = payload.get("type")
        jti: str | None = payload.get("jti")
        if user_id is None or token_type != "access":
            raise credentials_exception
    except PyJWTError as exc:
        raise credentials_exception from exc

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

    result = await db.execute(
        select(User)
        .options(selectinload(User.subscription))
        .where(User.id == _uuid.UUID(user_id))
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
