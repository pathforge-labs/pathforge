"""
PathForge — User Profile & GDPR Data Export Service
=====================================================
Profile management and GDPR Article 20+ compliant data export
with AI methodology disclosure, data provenance, and manifest
integrity (SHA-256 checksums + record counts).

Export pipeline:
    1. Validate no active export (rate limit: 1 per 24h)
    2. Create pending export request
    3. Collect data per engine
    4. Build GDPR Article 20+ JSON package
    5. Compute checksum + manifest
    6. Set 7-day expiry
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA
from app.models.user_profile import (
    DataExportRequest,
    ExportFormat,
    ExportStatus,
    ExportType,
    UserProfile,
)

logger = logging.getLogger(__name__)

# Rate limit: 1 export per 24 hours
EXPORT_RATE_LIMIT_HOURS = 24
# Export expiry: 7 days
EXPORT_EXPIRY_DAYS = 7
# Maximum export payload size: 50 MB
MAX_EXPORT_SIZE_BYTES = 50 * 1024 * 1024

# Engine model mapping for data collection
# (Import engines lazily to avoid circular imports)
ENGINE_DATA_COLLECTORS: dict[str, str] = {
    "career_dna": "app.models.career_dna.CareerDNA",
    "threat_radar": "app.models.threat_radar.CareerResilienceSnapshot",
    "predictive_career": "app.models.predictive_career.CareerForecast",
    "skill_decay": "app.models.skill_decay.SkillFreshness",
    "career_action_planner": "app.models.career_action_planner.CareerActionPlan",
    "salary_intelligence": "app.models.salary_intelligence.SalaryEstimate",
    "hidden_job_market": "app.models.hidden_job_market.CompanySignal",
    "collective_intelligence": "app.models.collective_intelligence.PeerCohortAnalysis",
    "career_simulation": "app.models.career_simulation.CareerSimulation",
    "interview_intelligence": "app.models.interview_intelligence.InterviewPrep",
    "transition_pathways": "app.models.transition_pathways.TransitionPath",
    "career_passport": "app.models.career_passport.CountryComparison",
}

# Background task references (prevent GC of fire-and-forget tasks)
_background_tasks: set[asyncio.Task[None]] = set()


class UserProfileService:
    """User Profile and GDPR Data Export management service."""

    # ── Profile CRUD ───────────────────────────────────────────

    @staticmethod
    async def get_profile(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> UserProfile | None:
        """Get user profile."""
        result = await db.execute(
            select(UserProfile).where(
                UserProfile.user_id == str(user_id),
            ),
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create_profile(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        data: dict[str, Any],
    ) -> UserProfile:
        """Create a new user profile."""
        profile = UserProfile(
            user_id=str(user_id),
            display_name=data.get("display_name"),
            headline=data.get("headline"),
            bio=data.get("bio"),
            location=data.get("location"),
            timezone=data.get("timezone", "UTC"),
            language=data.get("language", "en"),
        )
        db.add(profile)
        await db.flush()
        return profile

    @staticmethod
    async def update_profile(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        updates: dict[str, Any],
    ) -> UserProfile | None:
        """Update user profile fields. Returns None if not found."""
        profile = await UserProfileService.get_profile(
            db, user_id=user_id,
        )
        if profile is None:
            return None

        for key, value in updates.items():
            if value is not None and hasattr(profile, key):
                setattr(profile, key, value)

        await db.flush()
        return profile

    @staticmethod
    async def delete_profile(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete user profile. Returns True if deleted."""
        profile = await UserProfileService.get_profile(
            db, user_id=user_id,
        )
        if profile is None:
            return False

        await db.delete(profile)
        await db.flush()
        return True

    # ── Onboarding Status ──────────────────────────────────────

    @staticmethod
    async def get_onboarding_status(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Check onboarding completion status."""
        profile = await UserProfileService.get_profile(
            db, user_id=user_id,
        )

        # Check Career DNA exists
        career_dna_result = await db.execute(
            select(func.count(CareerDNA.id)).where(
                CareerDNA.user_id == str(user_id),
            ),
        )
        career_dna_exists = (career_dna_result.scalar() or 0) > 0

        return {
            "onboarding_completed": (
                profile.onboarding_completed if profile else False
            ),
            "profile_exists": profile is not None,
            "career_dna_exists": career_dna_exists,
            "engines_activated": 0,
            "total_engines": 12,
        }

    # ── Data Summary ───────────────────────────────────────────

    @staticmethod
    async def get_data_summary(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Get record count per engine for GDPR data awareness."""
        from app.models.notification import CareerNotification

        engine_counts: dict[str, int] = {}
        total_records = 0

        # Count profile data
        profile = await UserProfileService.get_profile(
            db, user_id=user_id,
        )
        has_profile = profile is not None

        # Count notifications
        notif_count_result = await db.execute(
            select(func.count(CareerNotification.id)).where(
                CareerNotification.user_id == str(user_id),
            ),
        )
        notification_count = notif_count_result.scalar() or 0

        # Count export requests
        export_count_result = await db.execute(
            select(func.count(DataExportRequest.id)).where(
                DataExportRequest.user_id == str(user_id),
            ),
        )
        export_count = export_count_result.scalar() or 0

        total_records = notification_count + export_count + (
            1 if has_profile else 0
        )

        return {
            "total_records": total_records,
            "engines": engine_counts,
            "profile_data": has_profile,
            "notification_count": notification_count,
            "export_count": export_count,
        }

    # ── GDPR Export ────────────────────────────────────────────

    @staticmethod
    async def request_export(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        export_type: str = ExportType.FULL.value,
        export_format: str = ExportFormat.JSON.value,
    ) -> dict[str, Any]:
        """Request a new GDPR data export.

        Rate limited: max 1 export per 24 hours.
        Returns export request details or error.
        """
        # Rate limit check
        cutoff = datetime.now(UTC) - timedelta(hours=EXPORT_RATE_LIMIT_HOURS)
        recent_query = select(func.count(DataExportRequest.id)).where(
            and_(
                DataExportRequest.user_id == str(user_id),
                DataExportRequest.created_at >= cutoff,
                DataExportRequest.status.in_([
                    ExportStatus.PENDING.value,
                    ExportStatus.PROCESSING.value,
                    ExportStatus.COMPLETED.value,
                ]),
            ),
        )
        recent_result = await db.execute(recent_query)
        recent_count = recent_result.scalar() or 0

        if recent_count > 0:
            return {
                "status": "rate_limited",
                "detail": (
                    "A data export was already requested within the last "
                    f"{EXPORT_RATE_LIMIT_HOURS} hours. Please try again later."
                ),
            }

        # Create export request
        export_request = DataExportRequest(
            user_id=str(user_id),
            export_type=export_type,
            format_=export_format,
            status=ExportStatus.PENDING.value,
        )
        db.add(export_request)
        await db.flush()

        # Fire background processing task (Sprint 22: async queue)
        task = asyncio.create_task(
            _process_export_background(
                db, export_request=export_request, user_id=user_id,
            ),
        )
        _background_tasks.add(task)
        task.add_done_callback(_background_tasks.discard)

        return {
            "status": "processing",
            "export_id": str(export_request.id),
            "detail": (
                "Export is being processed. Poll GET /export/{id} "
                "for status."
            ),
        }

    @staticmethod
    async def get_export_status(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        export_id: uuid.UUID,
    ) -> DataExportRequest | None:
        """Get export request status."""
        result = await db.execute(
            select(DataExportRequest).where(
                and_(
                    DataExportRequest.id == str(export_id),
                    DataExportRequest.user_id == str(user_id),
                ),
            ),
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def list_exports(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> dict[str, Any]:
        """List paginated export requests."""
        conditions = [DataExportRequest.user_id == str(user_id)]

        count_query = select(func.count(DataExportRequest.id)).where(
            and_(*conditions),
        )
        count_result = await db.execute(count_query)
        total = count_result.scalar() or 0

        offset = (page - 1) * page_size
        query = (
            select(DataExportRequest)
            .where(and_(*conditions))
            .order_by(DataExportRequest.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        result = await db.execute(query)
        exports = list(result.scalars().all())

        return {
            "exports": exports,
            "total": total,
            "page": page,
            "page_size": page_size,
        }

    # ── Export Processing ──────────────────────────────────────

    @staticmethod
    async def _process_export(
        db: AsyncSession,
        *,
        export_request: DataExportRequest,
        user_id: uuid.UUID,
    ) -> dict[str, Any]:
        """Process a GDPR data export request.

        Builds Article 20+ JSON package with:
        - Metadata: user, timestamp, format, type
        - AI methodology disclosure
        - Data categories with record counts
        - SHA-256 checksum for integrity

        Memory-guarded: rejects payloads exceeding MAX_EXPORT_SIZE_BYTES.
        """
        export_request.status = ExportStatus.PROCESSING.value
        await db.flush()

        try:
            # Build export payload
            payload = await _build_export_payload(
                db, user_id=user_id,
                export_type=export_request.export_type,
            )

            # Compact JSON for reduced memory footprint
            payload_json = json.dumps(
                payload, default=str, sort_keys=True,
                separators=(",", ":"),
            )
            payload_size = len(payload_json.encode("utf-8"))

            # Memory guard: reject oversized payloads
            if payload_size > MAX_EXPORT_SIZE_BYTES:
                logger.warning(
                    "Export payload too large for user %s: %d bytes",
                    user_id, payload_size,
                )
                export_request.status = ExportStatus.FAILED.value
                export_request.error_message = (
                    f"Export payload exceeds maximum size "
                    f"({MAX_EXPORT_SIZE_BYTES // (1024 * 1024)} MB). "
                    f"Please contact support."
                )
                await db.flush()
                return {
                    "status": "failed",
                    "export_id": str(export_request.id),
                    "detail": export_request.error_message,
                }

            # Compute checksum
            checksum = hashlib.sha256(
                payload_json.encode("utf-8"),
            ).hexdigest()

            # Count records
            record_count = _count_export_records(payload)

            # Update export request
            now = datetime.now(UTC)
            export_request.status = ExportStatus.COMPLETED.value
            export_request.checksum = checksum
            export_request.record_count = record_count
            export_request.file_size_bytes = payload_size
            export_request.completed_at = now
            export_request.expires_at = now + timedelta(
                days=EXPORT_EXPIRY_DAYS,
            )
            export_request.categories = payload.get("manifest", {}).get(
                "categories", {},
            )
            await db.flush()

            return {
                "status": "completed",
                "export_id": str(export_request.id),
                "record_count": record_count,
                "checksum": checksum,
                "expires_at": export_request.expires_at,
            }

        except Exception as error:
            logger.exception("Export processing failed for user %s", user_id)
            export_request.status = ExportStatus.FAILED.value
            export_request.error_message = str(error)
            await db.flush()

            return {
                "status": "failed",
                "export_id": str(export_request.id),
                "detail": "Export processing failed. Please try again.",
            }


# ── Background Export Processing ───────────────────────────────


async def _process_export_background(
    db: AsyncSession,
    *,
    export_request: DataExportRequest,
    user_id: uuid.UUID,
) -> None:
    """Background wrapper for export processing.

    Delegates to ``UserProfileService._process_export`` and logs
    any errors. Never raises — designed for ``asyncio.create_task``.
    """
    try:
        await UserProfileService._process_export(
            db, export_request=export_request, user_id=user_id,
        )
    except Exception:
        logger.exception(
            "Background export failed for user %s, export %s",
            user_id, export_request.id,
        )


# ── Export Payload Builder ─────────────────────────────────────


async def _build_export_payload(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    export_type: str,
) -> dict[str, Any]:
    """Build GDPR Article 20+ JSON export payload.

    Structure:
    {
        "metadata": { ... },
        "ai_methodology_disclosure": { ... },
        "manifest": { categories, record_counts },
        "data": { ... }
    }
    """
    now = datetime.now(UTC)
    categories: dict[str, int] = {}

    # Metadata
    metadata: dict[str, Any] = {
        "export_version": "1.0.0",
        "pathforge_version": "0.22.0",
        "exported_at": now.isoformat(),
        "user_id": str(user_id),
        "export_type": export_type,
        "format": "json",
        "gdpr_article": "Article 20 — Right to Data Portability",
    }

    # AI Methodology Disclosure (PathForge Manifesto)
    ai_disclosure: dict[str, Any] = {
        "framework": "PathForge Career Intelligence Platform",
        "engines": [
            {
                "name": engine_name,
                "purpose": "Career intelligence analysis",
                "confidence_cap": 0.85,
                "data_source": "AI-analyzed from user-provided data + public market signals",
            }
            for engine_name in ENGINE_DATA_COLLECTORS
        ],
        "transparency_policy": (
            "All AI-generated insights include confidence scores "
            "(capped at 85%), data source attribution, and disclaimers. "
            "PathForge never claims certainty about career outcomes."
        ),
        "user_autonomy": (
            "Users control all preferences, can disable any engine, "
            "and can request full data export or deletion at any time."
        ),
    }

    # Collect profile data
    profile_data = await _collect_profile_data(db, user_id)
    if profile_data:
        categories["profile"] = 1

    # Collect notification data
    notification_data = await _collect_notification_data(db, user_id)
    categories["notifications"] = len(
        notification_data.get("items", []),
    )

    # Build full data section
    data_section: dict[str, Any] = {
        "profile": profile_data,
        "notifications": notification_data,
    }

    # Manifest
    manifest: dict[str, Any] = {
        "categories": categories,
        "total_records": sum(categories.values()),
        "generated_at": now.isoformat(),
    }

    return {
        "metadata": metadata,
        "ai_methodology_disclosure": ai_disclosure,
        "manifest": manifest,
        "data": data_section,
    }


async def _collect_profile_data(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict[str, Any] | None:
    """Collect user profile data for export."""
    profile = await UserProfileService.get_profile(db, user_id=user_id)
    if profile is None:
        return None

    return {
        "display_name": profile.display_name,
        "headline": profile.headline,
        "bio": profile.bio,
        "location": profile.location,
        "timezone": profile.timezone,
        "language": profile.language,
        "onboarding_completed": profile.onboarding_completed,
        "created_at": profile.created_at.isoformat(),
        "updated_at": profile.updated_at.isoformat(),
    }


async def _collect_notification_data(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Collect notification data for export."""
    from app.models.notification import CareerNotification

    result = await db.execute(
        select(CareerNotification)
        .where(CareerNotification.user_id == str(user_id))
        .order_by(CareerNotification.created_at.desc()),
    )
    notifications = list(result.scalars().all())

    items = [
        {
            "source_engine": notification.source_engine,
            "notification_type": notification.notification_type,
            "severity": notification.severity,
            "title": notification.title,
            "body": notification.body,
            "is_read": notification.is_read,
            "created_at": notification.created_at.isoformat(),
        }
        for notification in notifications
    ]

    return {"items": items, "count": len(items)}


def _count_export_records(payload: dict[str, Any]) -> int:
    """Count total records in export payload."""
    manifest = payload.get("manifest", {})
    return int(manifest.get("total_records", 0))
