"""
PathForge API — User Routes
==============================
User profile management (protected endpoints).

Sprint 40 (Audit P0-1): GDPR Article 17 — account deletion endpoint.
"""

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request

from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.user import AccountDeletionResponse, UserResponse, UserUpdateRequest
from app.services.user_service import UserService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get the current authenticated user's profile",
)
@route_query_budget(max_queries=4)
async def get_me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
    summary="Update the current user's profile",
)
@route_query_budget(max_queries=6)
async def update_me(
    payload: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> User:
    update_data = payload.model_dump(exclude_unset=True)
    return await UserService.update_profile(db, current_user, **update_data)


@router.delete(
    "/me",
    response_model=AccountDeletionResponse,
    summary="Delete account and all data (GDPR Article 17)",
    description=(
        "Permanently deletes the user account and ALL associated data "
        "across all PathForge engines. This action is irreversible. "
        "Cancels any active Stripe subscription. Revokes all tokens."
    ),
)
@limiter.limit("2/hour")
@route_query_budget(max_queries=80)
async def delete_account(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    """GDPR Article 17 — Right to Erasure.

    Deletes all user data across all engine tables, cancels Stripe
    subscription, revokes tokens, and removes the user account.
    """
    from app.core.token_blacklist import token_blacklist
    from app.services.account_deletion_service import AccountDeletionService

    user_id = str(current_user.id)

    result = await AccountDeletionService.delete_account(
        db,
        user=current_user,
    )

    # Best-effort: blacklist current token to prevent reuse
    try:
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            import jwt as pyjwt

            from app.core.config import settings

            token = auth_header[7:]
            payload = pyjwt.decode(
                token,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
                options={"verify_exp": False},
            )
            jti = payload.get("jti")
            if jti:
                await token_blacklist.revoke(jti, ttl_seconds=3600)
    except Exception:
        logger.debug("Token blacklist on deletion — best effort failed")

    logger.info("Account deleted for user %s", user_id)

    return JSONResponse(
        status_code=200,
        content={
            "deleted": True,
            "message": (
                "Your account and all associated data have been permanently deleted. "
                "This action cannot be undone."
            ),
            "records_deleted": result["records_deleted"],
            "tables_affected": result["tables_affected"],
        },
    )
