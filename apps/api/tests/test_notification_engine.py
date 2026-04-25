"""
PathForge — Notification Engine™ Test Suite
=============================================
Tests for Sprint 22: models, enums, severity ordering, service helpers.

Coverage:
    - StrEnum values (Severity, NotificationType, DigestFrequency)
    - Model creation (CareerNotification, NotificationPreference, NotificationDigest)
    - Severity ordering for threshold checks
    - Schema validation (response models)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, time

from app.models.notification import (
    CareerNotification,
    DigestFrequency,
    NotificationDigest,
    NotificationPreference,
    NotificationType,
    Severity,
)
from app.schemas.notification import (
    CareerNotificationResponse,
    NotificationCountResponse,
    NotificationDigestResponse,
    NotificationListResponse,
    NotificationPreferenceResponse,
)
from app.services.notification_service import SEVERITY_ORDER

# ── Enum Tests ─────────────────────────────────────────────────


class TestEnums:
    """Test StrEnum definitions."""

    def test_severity_values(self) -> None:
        assert Severity.LOW == "low"
        assert Severity.MEDIUM == "medium"
        assert Severity.HIGH == "high"
        assert Severity.CRITICAL == "critical"

    def test_notification_type_values(self) -> None:
        assert NotificationType.THREAT == "threat"
        assert NotificationType.OPPORTUNITY == "opportunity"
        assert NotificationType.MILESTONE == "milestone"
        assert NotificationType.INSIGHT == "insight"
        assert NotificationType.ACTION_REQUIRED == "action_required"

    def test_digest_frequency_values(self) -> None:
        assert DigestFrequency.DAILY == "daily"
        assert DigestFrequency.WEEKLY == "weekly"


# ── Model Creation Tests ──────────────────────────────────────


class TestCareerNotificationModel:
    """Test CareerNotification model instantiation."""

    def test_create_notification(self) -> None:
        notification = CareerNotification(
            user_id=str(uuid.uuid4()),
            source_engine="threat_radar",
            notification_type="threat",
            severity="high",
            title="Industry disruption detected",
            body="AI regulation changes may affect your role.",
        )
        assert notification.source_engine == "threat_radar"
        assert notification.notification_type == "threat"
        assert notification.severity == "high"
        assert notification.title == "Industry disruption detected"
        assert notification.__tablename__ == "notif_career_notifications"

    def test_default_unread(self) -> None:
        # Column defaults are set at DB flush time, not __init__ time.
        # Verify the column-level default is configured correctly.
        col = CareerNotification.__table__.columns["is_read"]
        assert col.default.arg is False

    def test_with_metadata(self) -> None:
        notification = CareerNotification(
            user_id=str(uuid.uuid4()),
            source_engine="salary_intelligence",
            notification_type="insight",
            severity="low",
            title="Salary insight",
            body="Your market position has improved.",
            metadata_={"percentile": 75, "trend": "up"},
        )
        assert notification.metadata_ == {"percentile": 75, "trend": "up"}


class TestNotificationPreferenceModel:
    """Test NotificationPreference model instantiation."""

    def test_create_preference(self) -> None:
        pref = NotificationPreference(
            user_id=str(uuid.uuid4()),
            enabled_engines=["threat_radar", "skill_decay"],
            min_severity="medium",
            digest_frequency="weekly",
        )
        assert pref.enabled_engines == ["threat_radar", "skill_decay"]
        assert pref.min_severity == "medium"
        assert pref.digest_frequency == "weekly"
        assert pref.__tablename__ == "notif_preferences"

    def test_with_quiet_hours(self) -> None:
        pref = NotificationPreference(
            user_id=str(uuid.uuid4()),
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(8, 0),
        )
        assert pref.quiet_hours_start == time(22, 0)
        assert pref.quiet_hours_end == time(8, 0)


class TestNotificationDigestModel:
    """Test NotificationDigest model instantiation."""

    def test_create_digest(self) -> None:
        now = datetime.now(UTC)
        digest = NotificationDigest(
            user_id=str(uuid.uuid4()),
            digest_type="weekly",
            period_start=now,
            period_end=now,
            notification_count=15,
            summary={"by_severity": {"high": 3, "medium": 12}},
        )
        assert digest.digest_type == "weekly"
        assert digest.notification_count == 15
        assert digest.__tablename__ == "notif_digests"


# ── Severity Ordering Tests ───────────────────────────────────


class TestSeverityOrdering:
    """Test severity ordering for threshold comparison."""

    def test_ordering_values(self) -> None:
        assert SEVERITY_ORDER["low"] == 0
        assert SEVERITY_ORDER["medium"] == 1
        assert SEVERITY_ORDER["high"] == 2
        assert SEVERITY_ORDER["critical"] == 3

    def test_critical_above_all(self) -> None:
        assert SEVERITY_ORDER["critical"] > SEVERITY_ORDER["high"]
        assert SEVERITY_ORDER["critical"] > SEVERITY_ORDER["medium"]
        assert SEVERITY_ORDER["critical"] > SEVERITY_ORDER["low"]

    def test_low_below_all(self) -> None:
        assert SEVERITY_ORDER["low"] < SEVERITY_ORDER["medium"]
        assert SEVERITY_ORDER["low"] < SEVERITY_ORDER["high"]
        assert SEVERITY_ORDER["low"] < SEVERITY_ORDER["critical"]


# ── Schema Validation Tests ──────────────────────────────────


class TestSchemaValidation:
    """Test Pydantic response schemas accept model-like data."""

    def test_notification_response(self) -> None:
        data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "source_engine": "threat_radar",
            "notification_type": "threat",
            "severity": "high",
            "title": "Disruption detected",
            "body": "EU AI Act affects your role.",
            "is_read": False,
            "read_at": None,
            "action_url": None,
            "metadata": None,
            "created_at": datetime.now(UTC),
        }
        response = CareerNotificationResponse(**data)
        assert response.source_engine == "threat_radar"
        assert response.severity == "high"

    def test_notification_count_response(self) -> None:
        data = {
            "total_unread": 5,
            "by_severity": {
                "critical": 1,
                "high": 2,
                "medium": 1,
                "low": 1,
            },
            "by_engine": {
                "threat_radar": 2,
                "skill_decay": 3,
            },
        }
        response = NotificationCountResponse(**data)
        assert response.total_unread == 5

    def test_notification_list_response(self) -> None:
        data = {
            "notifications": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
            "has_next": False,
        }
        response = NotificationListResponse(**data)
        assert response.total == 0
        assert response.page == 1

    def test_preference_response(self) -> None:
        now = datetime.now(UTC)
        data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "enabled_engines": ["threat_radar"],
            "min_severity": "medium",
            "digest_enabled": True,
            "digest_frequency": "weekly",
            "quiet_hours_start": None,
            "quiet_hours_end": None,
            "in_app_notifications": True,
            "email_notifications": True,
            "push_notifications": False,
            "created_at": now,
            "updated_at": now,
        }
        response = NotificationPreferenceResponse(**data)
        assert response.min_severity == "medium"

    def test_digest_response(self) -> None:
        now = datetime.now(UTC)
        data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "digest_type": "weekly",
            "period_start": now,
            "period_end": now,
            "notification_count": 12,
            "summary": {"by_severity": {"high": 3}},
            "created_at": now,
        }
        response = NotificationDigestResponse(**data)
        assert response.notification_count == 12


# ── Service-Layer Tests (async, DB-backed) ────────────────────

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.notification_service import NotificationService


class TestEmitNotification:
    """Test NotificationService.emit_notification with preference filtering."""

    @pytest.mark.asyncio
    async def test_emit_creates_notification(
        self, db_session: AsyncSession,
    ) -> None:
        """Emit with no preferences → notification created."""
        user_id = uuid.uuid4()
        result = await NotificationService.emit_notification(
            db_session,
            user_id=user_id,
            source_engine="threat_radar",
            notification_type="threat",
            severity="high",
            title="Disruption detected",
            body="AI regulation changes may affect your role.",
        )
        assert result is not None
        assert result.source_engine == "threat_radar"
        assert result.severity == "high"
        assert result.title == "Disruption detected"

    @pytest.mark.asyncio
    async def test_emit_suppressed_by_engine_toggle(
        self, db_session: AsyncSession,
    ) -> None:
        """Disabled engine in preferences → returns None."""
        user_id = uuid.uuid4()
        # Create preferences with only skill_decay enabled
        await NotificationService.update_preferences(
            db_session,
            user_id=user_id,
            updates={"enabled_engines": ["skill_decay"]},
        )
        result = await NotificationService.emit_notification(
            db_session,
            user_id=user_id,
            source_engine="threat_radar",
            notification_type="threat",
            severity="high",
            title="Should be suppressed",
            body="Engine not enabled.",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_emit_suppressed_by_severity_threshold(
        self, db_session: AsyncSession,
    ) -> None:
        """Low severity below min_severity threshold → returns None."""
        user_id = uuid.uuid4()
        await NotificationService.update_preferences(
            db_session,
            user_id=user_id,
            updates={"min_severity": "high"},
        )
        result = await NotificationService.emit_notification(
            db_session,
            user_id=user_id,
            source_engine="threat_radar",
            notification_type="insight",
            severity="low",
            title="Should be suppressed",
            body="Below severity threshold.",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_emit_passes_severity_threshold(
        self, db_session: AsyncSession,
    ) -> None:
        """Critical severity above min_severity threshold → created."""
        user_id = uuid.uuid4()
        await NotificationService.update_preferences(
            db_session,
            user_id=user_id,
            updates={"min_severity": "high"},
        )
        result = await NotificationService.emit_notification(
            db_session,
            user_id=user_id,
            source_engine="threat_radar",
            notification_type="threat",
            severity="critical",
            title="Critical alert",
            body="Above threshold.",
        )
        assert result is not None
        assert result.severity == "critical"

    @pytest.mark.asyncio
    async def test_emit_with_metadata(
        self, db_session: AsyncSession,
    ) -> None:
        """Emit with engine-specific metadata → persisted correctly."""
        user_id = uuid.uuid4()
        metadata = {"percentile": 75, "trend": "up", "engine_version": "2.1"}
        result = await NotificationService.emit_notification(
            db_session,
            user_id=user_id,
            source_engine="salary_intelligence",
            notification_type="insight",
            severity="medium",
            title="Salary insight",
            body="Your market position improved.",
            metadata=metadata,
        )
        assert result is not None
        assert result.metadata_ == metadata


class TestListNotifications:
    """Test NotificationService.list_notifications pagination & filters."""

    @pytest.mark.asyncio
    async def test_list_basic_pagination(
        self, db_session: AsyncSession,
    ) -> None:
        """Returns correct page structure (total, has_next)."""
        user_id = uuid.uuid4()
        # Create 3 notifications
        for index in range(3):
            await NotificationService.emit_notification(
                db_session,
                user_id=user_id,
                source_engine="threat_radar",
                notification_type="threat",
                severity="medium",
                title=f"Alert {index}",
                body=f"Body {index}",
            )
        result = await NotificationService.list_notifications(
            db_session, user_id=user_id, page=1, page_size=2,
        )
        assert result["total"] == 3
        assert result["page"] == 1
        assert result["page_size"] == 2
        assert result["has_next"] is True
        assert len(result["notifications"]) == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_severity(
        self, db_session: AsyncSession,
    ) -> None:
        """Filter by severity returns only matching notifications."""
        user_id = uuid.uuid4()
        await NotificationService.emit_notification(
            db_session, user_id=user_id, source_engine="skill_decay",
            notification_type="threat", severity="high",
            title="High alert", body="High.",
        )
        await NotificationService.emit_notification(
            db_session, user_id=user_id, source_engine="skill_decay",
            notification_type="insight", severity="low",
            title="Low alert", body="Low.",
        )
        result = await NotificationService.list_notifications(
            db_session, user_id=user_id, severity="high",
        )
        assert result["total"] == 1
        assert result["notifications"][0].severity == "high"

    @pytest.mark.asyncio
    async def test_list_filter_by_engine(
        self, db_session: AsyncSession,
    ) -> None:
        """Filter by source_engine returns only matching notifications."""
        user_id = uuid.uuid4()
        await NotificationService.emit_notification(
            db_session, user_id=user_id, source_engine="threat_radar",
            notification_type="threat", severity="high",
            title="Threat", body="Threat.",
        )
        await NotificationService.emit_notification(
            db_session, user_id=user_id, source_engine="skill_decay",
            notification_type="insight", severity="low",
            title="Skill", body="Skill.",
        )
        result = await NotificationService.list_notifications(
            db_session, user_id=user_id, source_engine="skill_decay",
        )
        assert result["total"] == 1
        assert result["notifications"][0].source_engine == "skill_decay"


class TestUnreadCount:
    """Test NotificationService.get_unread_count with breakdowns."""

    @pytest.mark.asyncio
    async def test_unread_count_with_breakdown(
        self, db_session: AsyncSession,
    ) -> None:
        """Returns total + by_severity + by_engine."""
        user_id = uuid.uuid4()
        await NotificationService.emit_notification(
            db_session, user_id=user_id, source_engine="threat_radar",
            notification_type="threat", severity="critical",
            title="Critical A", body="A.",
        )
        await NotificationService.emit_notification(
            db_session, user_id=user_id, source_engine="skill_decay",
            notification_type="insight", severity="low",
            title="Low B", body="B.",
        )
        result = await NotificationService.get_unread_count(
            db_session, user_id=user_id,
        )
        assert result["total_unread"] == 2
        assert result["by_severity"]["critical"] == 1
        assert result["by_severity"]["low"] == 1
        assert result["by_engine"]["threat_radar"] == 1
        assert result["by_engine"]["skill_decay"] == 1

    @pytest.mark.asyncio
    async def test_unread_count_zero(
        self, db_session: AsyncSession,
    ) -> None:
        """No notifications → all zeros."""
        user_id = uuid.uuid4()
        result = await NotificationService.get_unread_count(
            db_session, user_id=user_id,
        )
        assert result["total_unread"] == 0


class TestMarkRead:
    """Test NotificationService.mark_read and mark_all_read."""

    @pytest.mark.asyncio
    async def test_mark_specific_read(
        self, db_session: AsyncSession,
    ) -> None:
        """Mark 2 of 3 as read → returns count 2."""
        user_id = uuid.uuid4()
        notifications = []
        for index in range(3):
            notification = await NotificationService.emit_notification(
                db_session, user_id=user_id, source_engine="threat_radar",
                notification_type="threat", severity="medium",
                title=f"Alert {index}", body=f"Body {index}",
            )
            assert notification is not None
            notifications.append(notification)

        ids_to_mark = [notifications[0].id, notifications[1].id]
        count = await NotificationService.mark_read(
            db_session,
            user_id=user_id,
            notification_ids=ids_to_mark,
        )
        assert count == 2

    @pytest.mark.asyncio
    async def test_mark_all_read(
        self, db_session: AsyncSession,
    ) -> None:
        """Mark all unread as read → returns total count."""
        user_id = uuid.uuid4()
        for index in range(4):
            await NotificationService.emit_notification(
                db_session, user_id=user_id, source_engine="threat_radar",
                notification_type="threat", severity="high",
                title=f"Alert {index}", body=f"Body {index}",
            )
        count = await NotificationService.mark_all_read(
            db_session, user_id=user_id,
        )
        assert count == 4
        # Verify none remain unread
        unread = await NotificationService.get_unread_count(
            db_session, user_id=user_id,
        )
        assert unread["total_unread"] == 0


class TestDigestGeneration:
    """Test NotificationService.generate_digest."""

    @pytest.mark.asyncio
    async def test_generate_weekly_digest(
        self, db_session: AsyncSession,
    ) -> None:
        """Creates digest with summary (by_severity, by_engine)."""
        user_id = uuid.uuid4()
        await NotificationService.emit_notification(
            db_session, user_id=user_id, source_engine="threat_radar",
            notification_type="threat", severity="high",
            title="Alert", body="Body.",
        )
        await NotificationService.emit_notification(
            db_session, user_id=user_id, source_engine="skill_decay",
            notification_type="insight", severity="medium",
            title="Skill", body="Decay.",
        )
        digest = await NotificationService.generate_digest(
            db_session, user_id=user_id, digest_type="weekly",
        )
        assert digest is not None
        assert digest.digest_type == "weekly"
        assert digest.notification_count == 2
        assert "by_severity" in digest.summary
        assert "by_engine" in digest.summary

    @pytest.mark.asyncio
    async def test_generate_daily_digest(
        self, db_session: AsyncSession,
    ) -> None:
        """Daily period uses 1-day window."""
        user_id = uuid.uuid4()
        await NotificationService.emit_notification(
            db_session, user_id=user_id, source_engine="threat_radar",
            notification_type="threat", severity="critical",
            title="Recent", body="Just now.",
        )
        digest = await NotificationService.generate_digest(
            db_session, user_id=user_id, digest_type="daily",
        )
        assert digest is not None
        assert digest.digest_type == "daily"
        assert digest.notification_count >= 1

    @pytest.mark.asyncio
    async def test_generate_digest_empty_period(
        self, db_session: AsyncSession,
    ) -> None:
        """No notifications in period → returns None."""
        user_id = uuid.uuid4()
        digest = await NotificationService.generate_digest(
            db_session, user_id=user_id, digest_type="weekly",
        )
        assert digest is None


class TestPreferenceCRUD:
    """Test NotificationService preference management."""

    @pytest.mark.asyncio
    async def test_get_preferences_none(
        self, db_session: AsyncSession,
    ) -> None:
        """No preferences → returns None."""
        user_id = uuid.uuid4()
        result = await NotificationService.get_preferences(
            db_session, user_id=user_id,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_create_preferences_via_update(
        self, db_session: AsyncSession,
    ) -> None:
        """Update when no preferences exist → creates new."""
        user_id = uuid.uuid4()
        pref = await NotificationService.update_preferences(
            db_session,
            user_id=user_id,
            updates={
                "min_severity": "high",
                "digest_frequency": "daily",
            },
        )
        assert pref is not None
        assert pref.min_severity == "high"
        assert pref.digest_frequency == "daily"

    @pytest.mark.asyncio
    async def test_update_existing_preferences(
        self, db_session: AsyncSession,
    ) -> None:
        """Update specific fields → others unchanged."""
        user_id = uuid.uuid4()
        # Create initial
        await NotificationService.update_preferences(
            db_session,
            user_id=user_id,
            updates={
                "min_severity": "low",
                "digest_frequency": "weekly",
                "enabled_engines": ["threat_radar", "skill_decay"],
            },
        )
        # Update only min_severity
        updated = await NotificationService.update_preferences(
            db_session,
            user_id=user_id,
            updates={"min_severity": "critical"},
        )
        assert updated.min_severity == "critical"
        assert updated.digest_frequency == "weekly"
        assert updated.enabled_engines == ["threat_radar", "skill_decay"]
