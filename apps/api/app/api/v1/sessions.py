"""
PathForge — User Session Management Routes (T1-extension, ADR-0011)
=====================================================================

User-facing surface on top of :class:`app.core.sessions.SessionRegistry`.

Three endpoints under ``/api/v1/users/me/sessions``:

  - ``GET    /``                       — list active sessions
  - ``DELETE /{jti}``                  — revoke a specific session
  - ``POST   /revoke-others``          — keep current, revoke the rest

All require an authenticated user. The current session JTI is read
from the cookie / bearer to mark the active row in the response and
to anchor the "revoke others" pivot.

CSRF
----

Mutating routes (``DELETE``, ``POST``) carry the
:func:`app.core.csrf.csrf_protect` dependency from ADR-0006 — the
double-submit pattern applies the same way as the rest of the
authenticated mutating surface.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from jwt import PyJWTError
from pydantic import BaseModel, ConfigDict

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.csrf import csrf_protect
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.core.sessions import SessionRegistry
from app.models.user import User

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users/me/sessions",
    tags=["Authentication", "Sessions"],
)


# ── Schemas ────────────────────────────────────────────────────


class SessionItem(BaseModel):
    """One active session row.

    The ``is_current`` flag lets the UI mark the device making the
    request so the user knows which row revokes their own session.
    """

    model_config = ConfigDict(from_attributes=True)

    jti: str
    device_label: str
    user_agent: str
    ip: str
    created_at: str
    last_seen_at: str
    is_current: bool


class SessionListResponse(BaseModel):
    sessions: list[SessionItem]


class RevokeOthersResponse(BaseModel):
    revoked_count: int


# ── Helpers ────────────────────────────────────────────────────


def _resolve_current_refresh_jti(request: Request) -> tuple[str | None, int]:
    """Read the refresh JTI of the device making this request from the
    ``pathforge_refresh`` cookie. Returns ``(jti, remaining_ttl_seconds)``.

    If the cookie is missing or the JWT is malformed (e.g. legacy
    bearer-only client), returns ``(None, 0)``. The handler treats
    "no current JTI" as "every session is foreign" — which is the
    correct semantics for a non-cookie client invoking the endpoint.
    """
    cookie = request.cookies.get("pathforge_refresh") or None
    if not cookie:
        return None, 0
    try:
        token_data = jwt.decode(
            cookie,
            settings.jwt_refresh_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except PyJWTError:
        return None, 0
    jti = token_data.get("jti")
    exp = token_data.get("exp")
    if not jti or not exp:
        return None, 0
    remaining = max(int(int(exp) - datetime.now(UTC).timestamp()), 1)
    return str(jti), remaining


# ── Routes ─────────────────────────────────────────────────────


@router.get(
    "",
    response_model=SessionListResponse,
    summary="List active sessions for the current user",
    description=(
        "Returns every refresh-token session currently known to the "
        "registry for the authenticated user. The session associated "
        "with the request itself is marked ``is_current=true`` so the "
        "UI can prevent accidental self-logout."
    ),
)
@route_query_budget(max_queries=4)
async def list_sessions(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> SessionListResponse:
    current_jti, _ = _resolve_current_refresh_jti(request)
    raw = await SessionRegistry.list_for_user(user_id=str(current_user.id))
    items = [
        SessionItem(
            jti=row.get("jti", ""),
            device_label=row.get("device_label", "Unknown device"),
            user_agent=row.get("user_agent", ""),
            ip=row.get("ip", ""),
            created_at=row.get("created_at", ""),
            last_seen_at=row.get("last_seen_at", ""),
            is_current=(row.get("jti") == current_jti),
        )
        for row in raw
    ]
    # Sort: current session first, then by last_seen_at descending.
    # Both ranks ascend toward "preferred", so a single descending sort on
    # the (is_current, last_seen_at) tuple groups True (1) above False (0)
    # and most-recent above older within each group.
    items.sort(key=lambda s: (s.is_current, s.last_seen_at), reverse=True)
    return SessionListResponse(sessions=items)


@router.delete(
    "/{jti}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke a specific session",
    description=(
        "Revokes a single session by its refresh JTI. The user can "
        "revoke any session they own (including the current one — "
        "doing so will sign them out on the next API call from that "
        "device)."
    ),
    dependencies=[Depends(csrf_protect)],
)
@limiter.limit("10/minute")
@route_query_budget(max_queries=4)
async def revoke_session(
    request: Request,
    jti: str,
    current_user: User = Depends(get_current_user),
) -> None:
    """Revoke a single session.

    The TTL we hand the blacklist is sized to the refresh-token expiry
    horizon (`jwt_refresh_token_expire_days`) — we don't have the
    exact ``exp`` for the targeted JTI without re-decoding it (and the
    user doesn't send the cookie of the *other* device), so we use
    the upper bound. Worst case we hold the blacklist entry slightly
    too long, which is a non-issue.
    """
    sessions = await SessionRegistry.list_for_user(
        user_id=str(current_user.id),
    )
    if not any(s.get("jti") == jti for s in sessions):
        # Don't reveal whether the JTI exists for another user.
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )
    ttl = settings.jwt_refresh_token_expire_days * 24 * 60 * 60
    ok = await SessionRegistry.revoke(
        user_id=str(current_user.id), jti=jti, ttl_seconds=ttl,
    )
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session registry temporarily unavailable.",
        )
    logger.info(
        "session.revoke: user=%s jti=%s…",
        current_user.id,
        jti[:8],
    )


@router.post(
    "/revoke-others",
    response_model=RevokeOthersResponse,
    summary="Sign out of all other devices",
    description=(
        "Revokes every active session for the user **except** the "
        "session associated with this request. The current device "
        "remains signed in."
    ),
    dependencies=[Depends(csrf_protect)],
)
@limiter.limit("5/minute")
@route_query_budget(max_queries=4)
async def revoke_others(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> RevokeOthersResponse:
    current_jti, _ = _resolve_current_refresh_jti(request)
    if current_jti is None:
        # The endpoint is only meaningful if the caller can identify
        # itself via the refresh cookie. A bearer-only legacy client
        # gets a clear 400 instead of accidentally revoking all its
        # own sessions.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "revoke-others requires the cookie auth path; "
                "your client is on the legacy bearer header."
            ),
        )
    ttl = settings.jwt_refresh_token_expire_days * 24 * 60 * 60
    revoked = await SessionRegistry.revoke_others(
        user_id=str(current_user.id),
        current_jti=current_jti,
        ttl_seconds=ttl,
    )
    logger.info(
        "session.revoke_others: user=%s revoked=%d",
        current_user.id,
        len(revoked),
    )
    return RevokeOthersResponse(revoked_count=len(revoked))


__all__ = ["RevokeOthersResponse", "SessionItem", "SessionListResponse", "router"]
