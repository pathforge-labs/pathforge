"""
PathForge — Feature Gate
=========================
Sprint 34: Tier-based feature gating as FastAPI dependency.

Design decisions:
    F34 — Config in Python dict (code-level, DB-driven future enhancement).
    Decoupled from engine services — gating is a middleware concern.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, status

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# ── Tier → Engine Access Matrix ─────────────────────────────────

TIER_ENGINES: dict[str, set[str]] = {
    "free": {"career_dna", "threat_radar"},
    "pro": {
        "career_dna",
        "threat_radar",
        "skill_decay",
        "salary_intelligence",
        "career_simulation",
        "interview_intelligence",
        "hidden_job_market",
        "collective_intelligence",
        "recommendation_intelligence",
        "career_action_planner",
    },
    "premium": {
        "career_dna",
        "threat_radar",
        "skill_decay",
        "salary_intelligence",
        "career_simulation",
        "interview_intelligence",
        "hidden_job_market",
        "collective_intelligence",
        "recommendation_intelligence",
        "career_action_planner",
        "career_passport",
        "predictive_career",
    },
}

TIER_SCAN_LIMITS: dict[str, int | None] = {
    "free": 3,
    "pro": 30,
    "premium": None,  # unlimited
}


def get_user_tier(user: User) -> str:
    """Resolve the current tier for a user.

    Falls back to 'free' if no subscription exists or billing is disabled.
    """
    if not settings.billing_enabled:
        return "free"

    subscription = getattr(user, "subscription", None)
    if subscription is None:
        return "free"

    if subscription.status in ("active", "trialing"):
        return str(subscription.tier)

    return "free"


def check_engine_access(tier: str, engine: str) -> bool:
    """Check if a tier grants access to a specific engine."""
    allowed_engines = TIER_ENGINES.get(tier, TIER_ENGINES["free"])
    return engine in allowed_engines


def get_scan_limit(tier: str) -> int | None:
    """Get the monthly scan limit for a tier. None = unlimited."""
    return TIER_SCAN_LIMITS.get(tier, TIER_SCAN_LIMITS["free"])


def require_feature(engine: str) -> Any:
    """FastAPI dependency factory for engine-level feature gating.

    Usage:
        @router.post("/analyze", dependencies=[Depends(require_feature("career_passport"))])
        async def analyze(...): ...

    Returns 403 with upgrade guidance if the user's tier lacks access.
    """
    from app.core.security import get_current_user

    async def _gate(current_user: User = Depends(get_current_user)) -> User:
        tier = get_user_tier(current_user)

        if not check_engine_access(tier, engine):
            # Determine the minimum required tier
            required_tier = "premium"
            for candidate_tier in ("pro", "premium"):
                if engine in TIER_ENGINES.get(candidate_tier, set()):
                    required_tier = candidate_tier
                    break

            logger.warning(
                "Feature gate blocked: user=%s engine=%s tier=%s required=%s",
                current_user.id,
                engine,
                tier,
                required_tier,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "feature_not_available",
                    "message": f"Engine '{engine}' requires {required_tier} tier or higher.",
                    "required_tier": required_tier,
                    "current_tier": tier,
                    "upgrade_url": "/api/v1/billing/checkout",
                },
            )

        return current_user

    return _gate
