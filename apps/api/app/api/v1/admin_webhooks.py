"""
PathForge — Admin Webhooks Routes (T6 / Sprint 58, ADR-0010)
================================================================

Operator surface for the webhook DLQ.  All routes are admin-only via
the ``require_admin`` dependency shared with the rest of
``app/api/v1/admin.py``.

Endpoints
---------

* ``GET  /api/v1/admin/webhooks?status=dlq`` — list ledger entries.
* ``POST /api/v1/admin/webhooks/{id}/replay`` — re-run a DLQ entry
  through the original handler.

Why a separate router (not folded into ``admin.py``)
-----------------------------------------------------

``admin.py`` is at the §2.1 file-length cap; rather than push it
over by inlining four more handlers, the DLQ surface gets its own
module.  Same admin-required dependency, same prefix, same OpenAPI
group — just a different file.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.admin import require_admin
from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.models.user import User
from app.models.webhook_event import WebhookEvent, WebhookOutcome
from app.services.billing_service import BillingService
from app.services.webhook_replay_service import (
    WebhookReplayError,
    WebhookReplayService,
)

router = APIRouter(prefix="/admin/webhooks", tags=["Admin — Webhooks"])


# ── Schemas ──────────────────────────────────────────────────


class WebhookEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider: str
    event_id: str
    event_type: str
    outcome: str = Field(
        ...,
        description=(
            "One of received / processed / failed / dlq. See "
            "`app.models.webhook_event.WebhookOutcome`."
        ),
    )
    retry_count: int
    last_error: str | None
    last_attempt_at: datetime | None
    created_at: datetime
    updated_at: datetime


class WebhookListResponse(BaseModel):
    items: list[WebhookEventResponse]
    total: int


class WebhookReplayResponse(BaseModel):
    id: uuid.UUID
    outcome: str
    replayed_at: datetime


# ── Replay handler dispatcher ────────────────────────────────


async def _dispatch_replay(
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Dispatch a replayed event to the same handler the original
    request would have hit.  Provider routing keys off the
    ``provider`` column already pulled out by the service layer —
    here we only see ``event_type`` + ``payload``, so we infer from
    the payload's shape.

    Stripe events carry an ``object: "event"`` key at the top level;
    Sentry alerts carry ``data.issue_alert``.  The dispatcher fans
    out by signature; unknown shapes raise so the admin sees
    "unhandled provider" rather than a silent no-op.
    """
    if payload.get("object") == "event":
        # Stripe Event payload — same shape `BillingService.process_webhook_event`
        # consumes from the production webhook.  We construct a fresh
        # session via the global factory because the admin route's
        # session is already in a transaction context.
        from app.core.database import async_session_factory

        async with async_session_factory() as session, session.begin():
            await BillingService.process_webhook_event(session, payload)
        return

    raise WebhookReplayError(
        f"Unhandled webhook payload shape for replay (event_type={event_type!s})"
    )


# ── Routes ───────────────────────────────────────────────────


@router.get(
    "",
    response_model=WebhookListResponse,
    summary="List webhook ledger entries",
    description=(
        "Admin-only.  Filter by ``status`` to scope the list "
        "(default ``dlq`` — the operator workflow we expect)."
    ),
)
@route_query_budget(max_queries=4)
async def list_webhook_events(
    status: Literal["received", "processed", "failed", "dlq"] = Query(
        "dlq",
        description="Outcome filter; defaults to the DLQ entries.",
    ),
    limit: int = Query(100, ge=1, le=500),
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> WebhookListResponse:
    service = WebhookReplayService(db)
    if status == "dlq":
        rows = await service.list_dlq(limit=limit)
    else:
        from sqlalchemy import select

        stmt = (
            select(WebhookEvent)
            .where(WebhookEvent.outcome == status)
            .order_by(WebhookEvent.created_at.desc())
            .limit(limit)
        )
        result = await db.execute(stmt)
        rows = list(result.scalars().all())
    items = [WebhookEventResponse.model_validate(row) for row in rows]
    return WebhookListResponse(items=items, total=len(items))


@router.post(
    "/{ledger_id}/replay",
    response_model=WebhookReplayResponse,
    summary="Replay a DLQ webhook entry",
    description=(
        "Admin-only.  Re-runs the persisted payload through the "
        "original handler.  Success transitions outcome to "
        "``processed``; failure keeps it in ``dlq`` and refreshes "
        "``last_error``."
    ),
)
@route_query_budget(max_queries=8)
async def replay_webhook_event(
    ledger_id: uuid.UUID,
    _admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> WebhookReplayResponse:
    service = WebhookReplayService(db)
    try:
        await service.replay(ledger_id, handler=_dispatch_replay)
    except WebhookReplayError as exc:
        # Surface the failure to the caller as 502 (gateway-style):
        # the replay reached the handler but the handler couldn't
        # complete.  The row stays at ``dlq``.
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    # Re-read so the response reflects the freshly-flushed outcome.
    from sqlalchemy import select

    stmt = select(WebhookEvent).where(WebhookEvent.id == ledger_id)
    row = (await db.execute(stmt)).scalar_one()
    return WebhookReplayResponse(
        id=row.id,
        outcome=row.outcome,
        replayed_at=row.last_attempt_at or datetime.now(tz=row.created_at.tzinfo),
    )


__all__ = ["WebhookOutcome", "router"]
