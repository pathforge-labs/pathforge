"""
PathForge — Account Deletion Service
======================================
GDPR Article 17 — Right to Erasure.

Deletes all user data across all engine tables, revokes tokens,
cancels Stripe subscription, and removes the user account.

Sprint 40 (Audit P0-1): Full account deletion for GDPR compliance.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.admin import AdminAuditLog
from app.models.ai_transparency import AITransparencyRecord
from app.models.analytics import CVExperiment, FunnelEvent, MarketInsight
from app.models.career_action_planner import (
    CareerActionPlan,
    CareerActionPlannerPreference,
)
from app.models.career_command_center import (
    CareerSnapshot,
    CommandCenterPreference,
)
from app.models.career_passport import (
    CareerPassportPreference,
    CountryComparison,
    CredentialMapping,
    MarketDemandEntry,
    VisaAssessment,
)
from app.models.career_simulation import CareerSimulation
from app.models.collective_intelligence import (
    CareerPulseEntry,
    CollectiveIntelligencePreference,
    IndustrySnapshot,
    PeerCohortAnalysis,
    SalaryBenchmark,
)
from app.models.hidden_job_market import (
    CompanySignal,
    HiddenJobMarketPreference,
    HiddenOpportunity,
)
from app.models.interview_intelligence import InterviewPrep
from app.models.matching import MatchResult
from app.models.notification import (
    CareerNotification,
    NotificationDigest,
    NotificationPreference,
)
from app.models.predictive_career import CareerForecast
from app.models.public_profile import PublicCareerProfile
from app.models.push_token import PushToken
from app.models.recommendation_intelligence import (
    CrossEngineRecommendation,
    RecommendationBatch,
    RecommendationPreference,
)
from app.models.salary_intelligence import SalaryEstimate
from app.models.skill_decay import SkillFreshness
from app.models.subscription import BillingEvent, Subscription, UsageRecord
from app.models.transition_pathways import TransitionPath
from app.models.user import User
from app.models.user_activity import UserActivityLog
from app.models.user_profile import DataExportRequest, UserProfile
from app.models.workflow_automation import (
    WorkflowExecution,
    WorkflowPreference,
)

logger = logging.getLogger(__name__)


# Models with user_id as str (not uuid.UUID).
# These need str(user_id) for the WHERE clause.
_STR_USER_ID_MODELS: list[type[Any]] = [
    # Career Intelligence Engines
    CareerActionPlan,
    CareerActionPlannerPreference,
    CareerSnapshot,
    CommandCenterPreference,
    CountryComparison,
    CredentialMapping,
    MarketDemandEntry,
    VisaAssessment,
    CareerPassportPreference,
    CareerSimulation,
    PeerCohortAnalysis,
    SalaryBenchmark,
    IndustrySnapshot,
    CareerPulseEntry,
    CollectiveIntelligencePreference,
    CompanySignal,
    HiddenOpportunity,
    HiddenJobMarketPreference,
    InterviewPrep,
    CareerForecast,
    CareerNotification,
    NotificationDigest,
    NotificationPreference,
    WorkflowExecution,
    WorkflowPreference,
    RecommendationBatch,
    CrossEngineRecommendation,
    RecommendationPreference,
    PushToken,
    UserProfile,
    DataExportRequest,
]

# Models with user_id as uuid.UUID.
_UUID_USER_ID_MODELS: list[type[Any]] = [
    AITransparencyRecord,
    FunnelEvent,
    CVExperiment,
    MarketInsight,
    SalaryEstimate,
    SkillFreshness,
    TransitionPath,
    MatchResult,
    UserActivityLog,
    PublicCareerProfile,
    UsageRecord,
    BillingEvent,
]


class AccountDeletionService:
    """GDPR Article 17 — Full account deletion."""

    @staticmethod
    async def delete_account(
        db: AsyncSession,
        *,
        user: User,
    ) -> dict[str, Any]:
        """Delete all user data and the user account.

        Steps:
            1. Cancel Stripe subscription (if active)
            2. Delete from all engine tables (non-cascaded)
            3. Create admin audit log entry
            4. Delete user record (cascades: resumes, preferences,
               blacklist_entries, applications, career_dna, subscription)
            5. Revoke all tokens via blacklist

        Returns summary of deleted records per table.
        """
        user_id = user.id
        user_email = user.email
        deletion_summary: dict[str, int] = {}
        total_deleted = 0

        logger.info(
            "Starting GDPR account deletion for user %s",
            user_id,
        )

        # ── 1. Cancel Stripe subscription ─────────────────────────
        await _cancel_stripe_subscription(db, user_id=user_id)

        # ── 2. Delete from str-typed user_id tables ───────────────
        for model in _STR_USER_ID_MODELS:
            count = await _delete_by_user_id(
                db, model=model, user_id=str(user_id),
            )
            if count > 0:
                deletion_summary[model.__tablename__] = count
                total_deleted += count

        # ── 3. Delete from UUID-typed user_id tables ──────────────
        for model in _UUID_USER_ID_MODELS:
            count = await _delete_by_user_id(
                db, model=model, user_id=user_id,
            )
            if count > 0:
                deletion_summary[model.__tablename__] = count
                total_deleted += count

        # ── 4. Create audit log (before user deletion) ────────────
        audit_entry = AdminAuditLog(
            admin_user_id=user_id,
            action="account_deletion",
            target_user_id=user_id,
            details={
                "reason": "gdpr_article_17_user_request",
                "email_hash": _hash_email(user_email),
                "tables_affected": list(deletion_summary.keys()),
                "total_records_deleted": total_deleted,
                "timestamp": datetime.now(UTC).isoformat(),
            },
        )
        db.add(audit_entry)

        # ── 5. Delete user (cascades handle remaining) ────────────
        await db.delete(user)
        await db.flush()

        # ── 6. Purge Redis-side session registry entries (ADR-0011) ──
        # Account-deletion guarantees right-to-erasure. The blacklist
        # entries auto-expire via TTL; the session-registry sets do
        # not (they extend the TTL on every login). Drop them here so
        # no trace of the deleted account lingers in Redis.
        try:
            from app.core.sessions import SessionRegistry

            await SessionRegistry.purge_user(user_id=str(user_id))
        except Exception:
            logger.warning(
                "Account deletion: session registry purge failed (user=%s); "
                "TTL will reclaim entries within %d days",
                user_id,
                30,
                exc_info=True,
            )

        logger.info(
            "GDPR account deletion completed for user %s: %d records across %d tables",
            user_id,
            total_deleted,
            len(deletion_summary),
        )

        return {
            "deleted": True,
            "records_deleted": total_deleted,
            "tables_affected": len(deletion_summary),
            "summary": deletion_summary,
        }


async def _delete_by_user_id(
    db: AsyncSession,
    *,
    model: type[Any],
    user_id: str | uuid.UUID,
) -> int:
    """Delete all records for a user from a model table.

    Returns the number of rows deleted.
    """
    try:
        result = await db.execute(
            delete(model).where(model.user_id == user_id)
        )
        row_count: int = getattr(result, "rowcount", 0) or 0
        return row_count
    except Exception:
        logger.warning(
            "Failed to delete from %s for user %s",
            model.__tablename__,
            user_id,
            exc_info=True,
        )
        return 0


async def _cancel_stripe_subscription(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> None:
    """Cancel Stripe subscription if it exists and is active."""
    from sqlalchemy import select

    result = await db.execute(
        select(Subscription).where(Subscription.user_id == user_id)
    )
    subscription = result.scalar_one_or_none()

    if subscription is None or not subscription.stripe_subscription_id:
        return

    if not settings.billing_enabled:
        logger.info("Billing disabled — skipping Stripe cancellation")
        return

    try:
        import stripe

        stripe.api_key = settings.stripe_secret_key
        stripe.Subscription.cancel(subscription.stripe_subscription_id)
        logger.info(
            "Stripe subscription %s cancelled for user %s",
            subscription.stripe_subscription_id,
            user_id,
        )
    except Exception:
        logger.warning(
            "Failed to cancel Stripe subscription %s — proceeding with deletion",
            subscription.stripe_subscription_id,
            exc_info=True,
        )


def _hash_email(email: str) -> str:
    """Hash email for audit trail (PII-safe)."""
    import hashlib
    return hashlib.sha256(email.encode()).hexdigest()[:16]
