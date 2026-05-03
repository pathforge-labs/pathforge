"""
PathForge — SSO Session-Revoke Webhook (T1-extension part 2, Sprint 62)
========================================================================

Enterprise-partner endpoint: an authorised admin calls
``POST /api/v1/internal/sso/logout`` to force-logout a PathForge user
(e.g. on employee offboarding).  PathForge immediately revokes every
active session for that user — both the Redis session-registry entries
(ADR-0011) and the JWT blacklist (ADR-0002) — so the next API call on
any of the user's devices is rejected.

Authentication
--------------

HMAC-SHA256 shared-secret, identical scheme to the Sentry auto-rollback
webhook (ADR-0009, ``sentry_webhook_secret``).  The secret lives in
``settings.sso_webhook_secret``.  An empty (unconfigured) secret makes
the endpoint **fail-closed**: every request is rejected with 401.
Configure the secret in the environment before exposing this endpoint
to a partner.

Payload
-------

::

    POST /api/v1/internal/sso/logout
    X-PathForge-Signature: <hex digest of HMAC-SHA256(secret, body)>
    Content-Type: application/json

    {"user_id": "<uuid4>", "reason": "offboarding"}

``reason`` is free-form (≤ 200 chars) and recorded in logs for audit
trail; it defaults to ``"offboarding"`` when omitted.  ``user_id``
must be a valid UUID4.  Unknown users (already-deleted accounts) are
treated as a no-op and return ``revoked_count: 0`` — the call is
idempotent.

Response
--------

``200 OK``: ``{"revoked_count": N, "user_id": "<uuid>"}``

``revoked_count`` is the number of sessions that were blacklisted and
removed from the registry.  Zero is valid (user already logged out or
no active sessions).

``401 Unauthorized``: missing or invalid signature.
``422 Unprocessable Entity``: malformed payload (pydantic validation).
``503 Service Unavailable``: Redis unreachable — the caller should retry.

Why fail-closed on Redis error
-------------------------------

Unlike the Sentry webhook (which fails-open so Sentry doesn't
retry-storm), the SSO logout is an admin-initiated action where the
expected outcome is a guaranteed logout.  A Redis outage means we
*cannot* fulfil that contract — returning 503 lets the caller retry
rather than silently accepting a revocation that never happened.

TTL for blacklisted JTIs
-------------------------

``SessionRegistry.list_for_user`` returns session metadata including the
JTI string.  To blacklist a JTI we need a ``ttl_seconds`` value.  The
per-JTI remaining TTL could be fetched from Redis (one extra ``TTL``
call per JTI), but the added round-trips complicate the code without
material benefit.  Instead we use ``settings.jwt_refresh_token_expire_days
* 86_400`` as a conservative upper bound.  Older tokens will have a
shorter true remaining lifetime, so the blacklist entry will linger at
most ``N days`` longer than strictly necessary — acceptable for a
security operation.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Header, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal/sso", tags=["Internal — SSO"])


# ── Signature helpers ─────────────────────────────────────────────────


def _verify_signature(secret: str, body: bytes, header_value: str) -> bool:
    """Constant-time HMAC-SHA256 check. Empty secret or blank header → False."""
    if not secret or not header_value:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header_value)


# ── Schemas ───────────────────────────────────────────────────────────


class SSOLogoutRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    user_id: str = Field(..., description="PathForge user UUID to force-logout")
    reason: str = Field(
        default="offboarding",
        max_length=200,
        description="Free-form reason recorded in the audit log",
    )

    @field_validator("user_id")
    @classmethod
    def _validate_uuid(cls, v: str) -> str:
        try:
            uuid.UUID(v, version=4)
        except ValueError as exc:
            raise ValueError("user_id must be a valid UUID4") from exc
        return v


class SSOLogoutResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    revoked_count: int
    user_id: str


# ── Helpers ───────────────────────────────────────────────────────────


async def _blacklist_sessions(
    user_id: str,
    sessions: list[dict[str, str]],
    max_ttl: int,
) -> list[str]:
    """Blacklist every JTI in *sessions* and return the revoked list.

    Raises ``HTTPException(503)`` if every blacklist write fails so the
    caller can propagate the failure without assuming a successful logout.
    """
    from app.core.token_blacklist import token_blacklist

    revoked: list[str] = []
    failures = 0
    for sess in sessions:
        jti = sess.get("jti", "")
        if not jti:
            continue
        try:
            await token_blacklist.revoke(jti, ttl_seconds=max_ttl)
            revoked.append(jti)
        except Exception:
            failures += 1
            logger.error(
                "sso-logout: blacklist.revoke failed (jti=%s… user=%s)",
                jti[:8], user_id, exc_info=True,
            )
    if failures > 0 and not revoked:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Session blacklist temporarily unavailable.",
        )
    return revoked


# ── Endpoint ──────────────────────────────────────────────────────────


@router.post(
    "/logout",
    response_model=SSOLogoutResponse,
    summary="SSO partner webhook — force-logout a user",
    description=(
        "Receives an admin logout event from an enterprise SSO partner "
        "and immediately revokes all active sessions for the target user. "
        "Requires HMAC-SHA256 signature in the ``X-PathForge-Signature`` header."
    ),
)
@limiter.limit("20/minute")
@route_query_budget(max_queries=1)
async def sso_logout(
    request: Request,
    x_pathforge_signature: Annotated[
        str | None, Header(alias="X-PathForge-Signature")
    ] = None,
) -> SSOLogoutResponse:
    secret = settings.sso_webhook_secret or ""
    body = await request.body()
    if not _verify_signature(secret, body, x_pathforge_signature or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-PathForge-Signature.",
        )
    payload = SSOLogoutRequest.model_validate_json(body)

    from app.core.sessions import SessionRegistry

    try:
        sessions = await SessionRegistry.list_for_user(user_id=payload.user_id)
    except Exception:
        logger.error("sso-logout: session registry unreachable (user=%s)", payload.user_id,
                     exc_info=True)
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="Session registry temporarily unavailable.") from None

    if not sessions:
        logger.info("sso-logout: no active sessions for user %s (reason=%s) — no-op",
                    payload.user_id, payload.reason)
        return SSOLogoutResponse(revoked_count=0, user_id=payload.user_id)

    max_ttl = settings.jwt_refresh_token_expire_days * 86_400
    revoked = await _blacklist_sessions(payload.user_id, sessions, max_ttl)
    await SessionRegistry.purge_user(user_id=payload.user_id)
    logger.info("sso-logout: revoked %d session(s) for user %s (reason=%s)",
                len(revoked), payload.user_id, payload.reason)
    return SSOLogoutResponse(revoked_count=len(revoked), user_id=payload.user_id)
