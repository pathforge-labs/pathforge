"""
PathForge — Billing API Routes
=================================
Sprint 34: Stripe billing endpoints.

7 endpoints: subscription, usage, features, checkout, portal, webhook, events.

Audit findings:
    F8  — Rate limits on billing endpoints
    F16 — Fast webhook ack (validate + persist → 200)
    F28 — Sentry context tagging
    F29 — OpenAPI tags
    F35 — Raw body reading for webhook signature
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.query_budget import route_query_budget
from app.core.rate_limit import limiter
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.subscription import (
    BillingEventResponse,
    CreateCheckoutSessionRequest,
    CreateCheckoutSessionResponse,
    CustomerPortalResponse,
    FeatureAccessResponse,
    SubscriptionResponse,
    UsageSummaryResponse,
)
from app.services.billing_service import BillingService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing"])


# ── GET /billing/subscription ──────────────────────────────────


@router.get(
    "/subscription",
    response_model=SubscriptionResponse,
    summary="Get current subscription",
    status_code=status.HTTP_200_OK,
)
@route_query_budget(max_queries=6)
async def get_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return the authenticated user's current subscription state."""
    subscription = await BillingService.get_or_create_subscription(db, current_user)
    return subscription


# ── GET /billing/usage ─────────────────────────────────────────


@router.get(
    "/usage",
    response_model=UsageSummaryResponse,
    summary="Get current period usage",
    status_code=status.HTTP_200_OK,
)
@route_query_budget(max_queries=8)
async def get_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return the authenticated user's AI scan usage for the current period."""
    return await BillingService.get_usage_summary(db, current_user)


# ── GET /billing/features ─────────────────────────────────────


@router.get(
    "/features",
    response_model=FeatureAccessResponse,
    summary="Get available features",
    status_code=status.HTTP_200_OK,
)
@route_query_budget(max_queries=8)
async def get_features(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Return which engines and scan limits are available for the user.

    Note (S4): This endpoint does NOT check billing_enabled because feature
    access must work regardless of billing state — free-tier users always
    get their default engines even when billing is disabled.
    """
    from app.core.feature_gate import TIER_ENGINES, TIER_SCAN_LIMITS, get_user_tier

    tier = get_user_tier(current_user)
    engines = list(TIER_ENGINES.get(tier, TIER_ENGINES["free"]))
    scan_limit = TIER_SCAN_LIMITS.get(tier, 3)

    summary = await BillingService.get_usage_summary(db, current_user)

    return {
        "tier": tier,
        "engines": engines,
        "scan_limit": scan_limit,
        "scans_remaining": summary.get("scans_remaining"),
        "billing_enabled": settings.billing_enabled,
    }


# ── POST /billing/checkout ────────────────────────────────────


@router.post(
    "/checkout",
    response_model=CreateCheckoutSessionResponse,
    summary="Create Stripe Checkout session",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_billing)  # S1: prevent checkout brute-force
@route_query_budget(max_queries=3)
async def create_checkout(
    request: Request,  # Required by slowapi rate limiter
    request_body: CreateCheckoutSessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a Stripe Checkout session for upgrading to a paid tier."""
    try:
        checkout_url = await BillingService.create_checkout_session(
            db,
            current_user,
            tier=request_body.tier,
            annual=request_body.annual,
            success_url=request_body.success_url,
            cancel_url=request_body.cancel_url,
        )
        return {"checkout_url": checkout_url}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── POST /billing/portal ──────────────────────────────────────


@router.post(
    "/portal",
    response_model=CustomerPortalResponse,
    summary="Create customer portal session",
    status_code=status.HTTP_200_OK,
)
@limiter.limit(settings.rate_limit_billing)  # S1: prevent portal abuse
@route_query_budget(max_queries=6)
async def create_portal(
    request: Request,  # Required by slowapi rate limiter
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a Stripe Customer Portal session for managing subscription."""
    try:
        portal_url = await BillingService.create_portal_session(db, current_user)
        return {"portal_url": portal_url}
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# ── GET /billing/events ───────────────────────────────────────


@router.get(
    "/events",
    response_model=list[BillingEventResponse],
    summary="List billing events (admin)",
    status_code=status.HTTP_200_OK,
)
@route_query_budget(max_queries=4)
async def list_events(
    request: Request,
    page: int = 1,
    per_page: int = 20,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_user),
) -> Any:
    """List billing events for admin dashboard. Requires admin role."""
    from app.api.v1.admin import require_admin as _check_admin

    await _check_admin(admin)
    return await BillingService.list_billing_events(db, page, per_page)


# ── Webhook Router ─────────────────────────────────────────────

webhook_router = APIRouter(prefix="/webhooks", tags=["Billing"])


@webhook_router.post(
    "/stripe",
    summary="Stripe webhook endpoint",
    status_code=status.HTTP_200_OK,
)
@limiter.limit("100/minute")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Handle Stripe webhook events.

    F16: Fast ack — validate signature + persist event → 200.
    F35: Uses Request.body() for raw bytes (required for signature verification).
    """
    # F35: Read raw body before any JSON parsing
    payload = await request.body()
    signature = request.headers.get("stripe-signature", "")

    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing stripe-signature header",
        )

    try:
        event = BillingService.verify_webhook_signature(payload, signature)
    except Exception as exc:
        logger.warning("Webhook signature verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid webhook signature",
        ) from exc

    # F16: Process event (fast — just DB writes)
    try:
        await BillingService.process_webhook_event(db, event)
        await db.commit()
    except Exception:
        logger.exception("Webhook processing error for event %s", event.get("id"))
        # F28: Sentry context
        try:
            import sentry_sdk

            sentry_sdk.set_tag("module", "billing")
            sentry_sdk.set_tag("stripe_event_type", event.get("type", "unknown"))
        except ImportError:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Webhook processing failed",
        ) from None

    return {"status": "ok"}
