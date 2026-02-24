"""
PathForge API — Auth Routes
=============================
Registration, login, token refresh, and logout endpoints.
"""

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from jwt import PyJWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    oauth2_scheme,
)
from app.core.token_blacklist import token_blacklist
from app.models.user import User
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        return await UserService.create_user(
            db,
            email=payload.email,
            password=payload.password,
            full_name=payload.full_name,
        )
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
async def login(
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
async def refresh_token(
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
            from datetime import UTC, datetime

            remaining = max(int(exp - datetime.now(UTC).timestamp()), 1)
            await token_blacklist.revoke(jti, ttl_seconds=remaining)
    except PyJWTError:
        pass  # Token already invalid — nothing to revoke
