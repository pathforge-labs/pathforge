"""
PathForge — UserProfileService Extended Test Suite
=====================================================
Service-method level tests with mocked AsyncSession. Complements
``test_user_profile.py`` (which covers models, enums, schemas and
integration-style CRUD via a real db_session fixture).

This module focuses on the exact control-flow branches of each
service method using ``AsyncMock`` / ``MagicMock`` — no real DB.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user_profile import (
    DataExportRequest,
    ExportFormat,
    ExportStatus,
    ExportType,
    UserProfile,
)
from app.services.user_profile_service import (
    EXPORT_EXPIRY_DAYS,
    MAX_EXPORT_SIZE_BYTES,
    UserProfileService,
    _build_export_payload,
    _collect_notification_data,
    _collect_profile_data,
)

pytestmark = pytest.mark.asyncio


# ── Helpers ────────────────────────────────────────────────────


def _make_db() -> AsyncMock:
    """Build an AsyncSession mock where ``add`` is a sync MagicMock.

    SQLAlchemy's ``Session.add`` / ``Session.delete`` are synchronous.
    Overriding them on the AsyncMock avoids spurious "coroutine never
    awaited" warnings from service code that calls them without await.
    """
    db = AsyncMock()
    db.add = MagicMock()
    return db


def _make_scalar_result(value: Any) -> MagicMock:
    """Build a MagicMock whose ``scalar_one_or_none`` returns ``value``."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalar.return_value = value
    return result


def _make_scalars_result(values: list[Any]) -> MagicMock:
    """Build a MagicMock whose ``scalars().all()`` returns ``values``."""
    result = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = values
    result.scalars.return_value = scalars
    return result


def _make_profile(
    user_id: uuid.UUID,
    *,
    display_name: str = "Test User",
    headline: str | None = "Engineer",
    bio: str | None = "Bio",
    location: str | None = "NL",
    timezone: str = "UTC",
    language: str = "en",
    onboarding_completed: bool = False,
) -> UserProfile:
    """Create an in-memory UserProfile without touching the DB."""
    profile = UserProfile(
        user_id=str(user_id),
        display_name=display_name,
        headline=headline,
        bio=bio,
        location=location,
        timezone=timezone,
        language=language,
    )
    profile.onboarding_completed = onboarding_completed
    now = datetime.now(UTC)
    profile.created_at = now
    profile.updated_at = now
    return profile


def _make_export(
    user_id: uuid.UUID,
    *,
    status: str = ExportStatus.PENDING.value,
    export_type: str = ExportType.FULL.value,
) -> DataExportRequest:
    """Create an in-memory DataExportRequest."""
    export = DataExportRequest(
        user_id=str(user_id),
        export_type=export_type,
        format_=ExportFormat.JSON.value,
        status=status,
    )
    export.id = uuid.uuid4()
    export.created_at = datetime.now(UTC)
    return export


# ── get_profile ────────────────────────────────────────────────


class TestGetProfile:
    """UserProfileService.get_profile branches."""

    async def test_returns_profile_when_found(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(profile)

        result = await UserProfileService.get_profile(db, user_id=user_id)

        assert result is profile
        db.execute.assert_awaited_once()

    async def test_returns_none_when_not_found(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        result = await UserProfileService.get_profile(db, user_id=user_id)

        assert result is None

    async def test_queries_with_string_user_id(self) -> None:
        """user_id is coerced to string in the WHERE clause."""
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        await UserProfileService.get_profile(db, user_id=user_id)

        assert db.execute.await_count == 1


# ── create_profile ─────────────────────────────────────────────


class TestCreateProfile:
    """UserProfileService.create_profile branches."""

    async def test_creates_with_all_fields(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()

        profile = await UserProfileService.create_profile(
            db,
            user_id=user_id,
            data={
                "display_name": "Emre",
                "headline": "Engineer",
                "bio": "Hi",
                "location": "NL",
                "timezone": "Europe/Amsterdam",
                "language": "tr",
            },
        )

        assert profile.display_name == "Emre"
        assert profile.headline == "Engineer"
        assert profile.bio == "Hi"
        assert profile.location == "NL"
        assert profile.timezone == "Europe/Amsterdam"
        assert profile.language == "tr"
        assert profile.user_id == str(user_id)
        db.add.assert_called_once_with(profile)
        db.flush.assert_awaited_once()

    async def test_applies_timezone_default(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()

        profile = await UserProfileService.create_profile(
            db, user_id=user_id, data={"display_name": "X"},
        )

        assert profile.timezone == "UTC"

    async def test_applies_language_default(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()

        profile = await UserProfileService.create_profile(
            db, user_id=user_id, data={"display_name": "X"},
        )

        assert profile.language == "en"

    async def test_empty_data_still_creates_profile(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()

        profile = await UserProfileService.create_profile(
            db, user_id=user_id, data={},
        )

        assert profile.display_name is None
        assert profile.headline is None
        assert profile.timezone == "UTC"
        db.add.assert_called_once()

    async def test_flush_called_after_add(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()

        await UserProfileService.create_profile(
            db, user_id=user_id, data={"display_name": "X"},
        )

        db.add.assert_called_once()
        db.flush.assert_awaited_once()


# ── update_profile ─────────────────────────────────────────────


class TestUpdateProfile:
    """UserProfileService.update_profile branches."""

    async def test_returns_none_when_profile_missing(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        result = await UserProfileService.update_profile(
            db, user_id=user_id, updates={"headline": "New"},
        )

        assert result is None

    async def test_updates_existing_fields(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(user_id, headline="Old")
        db = _make_db()
        db.execute.return_value = _make_scalar_result(profile)

        result = await UserProfileService.update_profile(
            db, user_id=user_id, updates={"headline": "New"},
        )

        assert result is profile
        assert result.headline == "New"
        db.flush.assert_awaited()

    async def test_ignores_none_values(self) -> None:
        """None in updates dict does not clobber the existing value."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id, headline="Keep")
        db = _make_db()
        db.execute.return_value = _make_scalar_result(profile)

        result = await UserProfileService.update_profile(
            db, user_id=user_id, updates={"headline": None, "bio": "NewBio"},
        )

        assert result is not None
        assert result.headline == "Keep"
        assert result.bio == "NewBio"

    async def test_ignores_unknown_attributes(self) -> None:
        """Keys not on the model are silently skipped."""
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(profile)

        result = await UserProfileService.update_profile(
            db,
            user_id=user_id,
            updates={"nonexistent_field": "x", "bio": "ok"},
        )

        assert result is not None
        assert result.bio == "ok"
        assert not hasattr(result, "nonexistent_field") or \
            getattr(result, "nonexistent_field", None) != "x"

    async def test_updates_multiple_fields(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(profile)

        result = await UserProfileService.update_profile(
            db,
            user_id=user_id,
            updates={
                "headline": "H",
                "bio": "B",
                "location": "L",
                "language": "nl",
            },
        )

        assert result is not None
        assert result.headline == "H"
        assert result.bio == "B"
        assert result.location == "L"
        assert result.language == "nl"


# ── delete_profile ─────────────────────────────────────────────


class TestDeleteProfile:
    """UserProfileService.delete_profile branches."""

    async def test_returns_false_when_missing(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        result = await UserProfileService.delete_profile(
            db, user_id=user_id,
        )

        assert result is False
        db.delete.assert_not_called()

    async def test_returns_true_and_deletes_when_found(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(profile)

        result = await UserProfileService.delete_profile(
            db, user_id=user_id,
        )

        assert result is True
        db.delete.assert_awaited_once_with(profile)
        db.flush.assert_awaited()


# ── get_onboarding_status ──────────────────────────────────────


class TestGetOnboardingStatus:
    """UserProfileService.get_onboarding_status branches."""

    async def test_no_profile_no_career_dna(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(None),   # profile lookup
            _make_scalar_result(0),      # career_dna count
        ]

        status = await UserProfileService.get_onboarding_status(
            db, user_id=user_id,
        )

        assert status["profile_exists"] is False
        assert status["onboarding_completed"] is False
        assert status["career_dna_exists"] is False
        assert status["engines_activated"] == 0
        assert status["total_engines"] == 12

    async def test_profile_without_career_dna(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(user_id, onboarding_completed=False)
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(profile),
            _make_scalar_result(0),
        ]

        status = await UserProfileService.get_onboarding_status(
            db, user_id=user_id,
        )

        assert status["profile_exists"] is True
        assert status["career_dna_exists"] is False
        assert status["onboarding_completed"] is False

    async def test_profile_with_career_dna(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(user_id, onboarding_completed=True)
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(profile),
            _make_scalar_result(1),
        ]

        status = await UserProfileService.get_onboarding_status(
            db, user_id=user_id,
        )

        assert status["profile_exists"] is True
        assert status["career_dna_exists"] is True
        assert status["onboarding_completed"] is True

    async def test_career_dna_count_null_coerced_to_zero(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(None),
            _make_scalar_result(None),  # scalar() returns None
        ]

        status = await UserProfileService.get_onboarding_status(
            db, user_id=user_id,
        )

        assert status["career_dna_exists"] is False

    async def test_multiple_career_dna_rows_still_true(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(profile),
            _make_scalar_result(5),
        ]

        status = await UserProfileService.get_onboarding_status(
            db, user_id=user_id,
        )

        assert status["career_dna_exists"] is True


# ── request_export ─────────────────────────────────────────────


class TestRequestExport:
    """UserProfileService.request_export branches."""

    async def test_rate_limited_when_recent_export_exists(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(1)

        result = await UserProfileService.request_export(
            db, user_id=user_id,
        )

        assert result["status"] == "rate_limited"
        assert "24 hours" in result["detail"]
        db.add.assert_not_called()

    async def test_success_creates_pending_export(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(0)

        with patch(
            "app.services.user_profile_service.asyncio.create_task",
        ) as fake_create_task:
            fake_create_task.return_value = MagicMock()
            result = await UserProfileService.request_export(
                db, user_id=user_id,
            )

        assert result["status"] == "processing"
        assert "export_id" in result
        db.add.assert_called_once()
        db.flush.assert_awaited()
        fake_create_task.assert_called_once()

    async def test_rate_limit_count_zero_proceeds(self) -> None:
        """scalar() → 0 must NOT be treated as rate-limited."""
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(0)

        with patch(
            "app.services.user_profile_service.asyncio.create_task",
        ) as fake_create_task:
            fake_create_task.return_value = MagicMock()
            result = await UserProfileService.request_export(
                db, user_id=user_id,
            )

        assert result["status"] == "processing"

    async def test_passes_custom_export_type_to_created_request(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(0)

        with patch(
            "app.services.user_profile_service.asyncio.create_task",
        ) as fake_create_task:
            fake_create_task.return_value = MagicMock()
            await UserProfileService.request_export(
                db,
                user_id=user_id,
                export_type=ExportType.CAREER_DNA_ONLY.value,
            )

        added: DataExportRequest = db.add.call_args.args[0]
        assert added.export_type == ExportType.CAREER_DNA_ONLY.value
        assert added.status == ExportStatus.PENDING.value
        assert added.user_id == str(user_id)

    async def test_rate_limit_null_count_proceeds(self) -> None:
        """scalar() returning None is coerced to 0 and does not rate-limit."""
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        with patch(
            "app.services.user_profile_service.asyncio.create_task",
        ) as fake_create_task:
            fake_create_task.return_value = MagicMock()
            result = await UserProfileService.request_export(
                db, user_id=user_id,
            )

        assert result["status"] == "processing"


# ── get_export_status ──────────────────────────────────────────


class TestGetExportStatus:
    """UserProfileService.get_export_status branches."""

    async def test_returns_none_when_not_found(self) -> None:
        user_id = uuid.uuid4()
        export_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        result = await UserProfileService.get_export_status(
            db, user_id=user_id, export_id=export_id,
        )

        assert result is None

    async def test_returns_export_when_found(self) -> None:
        user_id = uuid.uuid4()
        export = _make_export(user_id, status=ExportStatus.COMPLETED.value)
        db = _make_db()
        db.execute.return_value = _make_scalar_result(export)

        result = await UserProfileService.get_export_status(
            db, user_id=user_id, export_id=export.id,
        )

        assert result is export
        assert result.status == ExportStatus.COMPLETED.value

    async def test_queries_once(self) -> None:
        user_id = uuid.uuid4()
        export_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        await UserProfileService.get_export_status(
            db, user_id=user_id, export_id=export_id,
        )

        assert db.execute.await_count == 1


# ── list_exports ───────────────────────────────────────────────


class TestListExports:
    """UserProfileService.list_exports branches."""

    async def test_empty_list(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(0),         # count
            _make_scalars_result([]),       # rows
        ]

        result = await UserProfileService.list_exports(
            db, user_id=user_id,
        )

        assert result["exports"] == []
        assert result["total"] == 0
        assert result["page"] == 1
        assert result["page_size"] == 20

    async def test_multiple_exports(self) -> None:
        user_id = uuid.uuid4()
        exports = [
            _make_export(user_id, status=ExportStatus.COMPLETED.value),
            _make_export(user_id, status=ExportStatus.PENDING.value),
            _make_export(user_id, status=ExportStatus.FAILED.value),
        ]
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(3),
            _make_scalars_result(exports),
        ]

        result = await UserProfileService.list_exports(
            db, user_id=user_id,
        )

        assert result["total"] == 3
        assert len(result["exports"]) == 3
        assert result["exports"][0] is exports[0]

    async def test_pagination_parameters(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(42),
            _make_scalars_result([]),
        ]

        result = await UserProfileService.list_exports(
            db, user_id=user_id, page=3, page_size=5,
        )

        assert result["page"] == 3
        assert result["page_size"] == 5
        assert result["total"] == 42

    async def test_null_count_coerced_to_zero(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(None),
            _make_scalars_result([]),
        ]

        result = await UserProfileService.list_exports(
            db, user_id=user_id,
        )

        assert result["total"] == 0


# ── _build_export_payload ──────────────────────────────────────


class TestBuildExportPayload:
    """_build_export_payload GDPR Article 20+ structure."""

    async def test_has_all_top_level_keys(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        # profile lookup (None) + notifications query (empty)
        db.execute.side_effect = [
            _make_scalar_result(None),
            _make_scalars_result([]),
        ]

        payload = await _build_export_payload(
            db, user_id=user_id, export_type=ExportType.FULL.value,
        )

        assert set(payload.keys()) == {
            "metadata", "ai_methodology_disclosure",
            "manifest", "data",
        }

    async def test_metadata_fields(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(None),
            _make_scalars_result([]),
        ]

        payload = await _build_export_payload(
            db, user_id=user_id, export_type=ExportType.FULL.value,
        )

        meta = payload["metadata"]
        assert meta["user_id"] == str(user_id)
        assert meta["export_type"] == ExportType.FULL.value
        assert meta["format"] == "json"
        assert meta["export_version"] == "1.0.0"
        assert "Article 20" in meta["gdpr_article"]

    async def test_ai_methodology_disclosure_engines_listed(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(None),
            _make_scalars_result([]),
        ]

        payload = await _build_export_payload(
            db, user_id=user_id, export_type=ExportType.FULL.value,
        )

        disclosure = payload["ai_methodology_disclosure"]
        assert disclosure["framework"] == (
            "PathForge Career Intelligence Platform"
        )
        assert len(disclosure["engines"]) >= 12
        assert all(
            engine["confidence_cap"] == 0.85
            for engine in disclosure["engines"]
        )
        assert "transparency_policy" in disclosure
        assert "user_autonomy" in disclosure

    async def test_profile_counted_when_present(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(profile),     # profile lookup
            _make_scalars_result([]),         # notifications
        ]

        payload = await _build_export_payload(
            db, user_id=user_id, export_type=ExportType.FULL.value,
        )

        assert payload["manifest"]["categories"]["profile"] == 1
        assert payload["data"]["profile"]["display_name"] == "Test User"

    async def test_profile_absent_not_in_categories(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(None),
            _make_scalars_result([]),
        ]

        payload = await _build_export_payload(
            db, user_id=user_id, export_type=ExportType.FULL.value,
        )

        assert "profile" not in payload["manifest"]["categories"]
        assert payload["data"]["profile"] is None

    async def test_manifest_total_is_sum_of_category_counts(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(user_id)
        db = _make_db()
        db.execute.side_effect = [
            _make_scalar_result(profile),
            _make_scalars_result([]),  # no notifications
        ]

        payload = await _build_export_payload(
            db, user_id=user_id, export_type=ExportType.FULL.value,
        )

        categories = payload["manifest"]["categories"]
        assert payload["manifest"]["total_records"] == sum(
            categories.values(),
        )


# ── _collect_profile_data ──────────────────────────────────────


class TestCollectProfileData:
    """_collect_profile_data branches."""

    async def test_none_when_profile_missing(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        result = await _collect_profile_data(db, user_id)

        assert result is None

    async def test_returns_serialisable_dict(self) -> None:
        user_id = uuid.uuid4()
        profile = _make_profile(
            user_id,
            display_name="Alice",
            headline="Head",
            bio="Bio",
            location="NL",
            timezone="UTC",
            language="en",
        )
        db = _make_db()
        db.execute.return_value = _make_scalar_result(profile)

        result = await _collect_profile_data(db, user_id)

        assert result is not None
        assert result["display_name"] == "Alice"
        assert result["headline"] == "Head"
        assert isinstance(result["created_at"], str)
        assert isinstance(result["updated_at"], str)


# ── _collect_notification_data ─────────────────────────────────


class TestCollectNotificationData:
    """_collect_notification_data branches."""

    async def test_empty_returns_zero_items(self) -> None:
        user_id = uuid.uuid4()
        db = _make_db()
        db.execute.return_value = _make_scalars_result([])

        result = await _collect_notification_data(db, user_id)

        assert result == {"items": [], "count": 0}

    async def test_notifications_mapped_to_dicts(self) -> None:
        user_id = uuid.uuid4()
        notif = MagicMock()
        notif.source_engine = "career_dna"
        notif.notification_type = "info"
        notif.severity = "low"
        notif.title = "Welcome"
        notif.body = "Hello"
        notif.is_read = False
        notif.created_at = datetime.now(UTC)
        db = _make_db()
        db.execute.return_value = _make_scalars_result([notif])

        result = await _collect_notification_data(db, user_id)

        assert result["count"] == 1
        assert result["items"][0]["title"] == "Welcome"
        assert result["items"][0]["source_engine"] == "career_dna"
        assert isinstance(result["items"][0]["created_at"], str)


# ── _process_export ────────────────────────────────────────────


class TestProcessExport:
    """UserProfileService._process_export pipeline branches."""

    async def test_success_sets_completed_fields(self) -> None:
        user_id = uuid.uuid4()
        export = _make_export(user_id)
        db = _make_db()

        fake_payload: dict[str, Any] = {
            "metadata": {"user_id": str(user_id)},
            "manifest": {
                "total_records": 3,
                "categories": {"profile": 1, "notifications": 2},
            },
            "data": {},
        }

        with patch(
            "app.services.user_profile_service._build_export_payload",
            new=AsyncMock(return_value=fake_payload),
        ):
            result = await UserProfileService._process_export(
                db, export_request=export, user_id=user_id,
            )

        assert result["status"] == "completed"
        assert result["export_id"] == str(export.id)
        assert result["record_count"] == 3
        assert export.status == ExportStatus.COMPLETED.value
        assert export.record_count == 3
        assert export.checksum is not None
        assert len(export.checksum) == 64  # SHA-256 hex length
        assert export.file_size_bytes is not None
        assert export.file_size_bytes > 0
        assert export.completed_at is not None
        assert export.expires_at is not None
        # 7 day expiry window
        delta = export.expires_at - export.completed_at
        assert abs(delta - timedelta(days=EXPORT_EXPIRY_DAYS)) < (
            timedelta(seconds=1)
        )
        assert export.categories == {"profile": 1, "notifications": 2}

    async def test_failure_marks_failed_and_stores_error(self) -> None:
        user_id = uuid.uuid4()
        export = _make_export(user_id)
        db = _make_db()

        with patch(
            "app.services.user_profile_service._build_export_payload",
            new=AsyncMock(side_effect=RuntimeError("boom")),
        ):
            result = await UserProfileService._process_export(
                db, export_request=export, user_id=user_id,
            )

        assert result["status"] == "failed"
        assert export.status == ExportStatus.FAILED.value
        assert export.error_message == "boom"

    async def test_oversized_payload_is_rejected(self) -> None:
        user_id = uuid.uuid4()
        export = _make_export(user_id)
        db = _make_db()

        # Build a payload whose JSON size > MAX_EXPORT_SIZE_BYTES
        huge_blob = "x" * (MAX_EXPORT_SIZE_BYTES + 1024)
        fake_payload: dict[str, Any] = {
            "metadata": {},
            "manifest": {"total_records": 1, "categories": {}},
            "data": {"blob": huge_blob},
        }

        with patch(
            "app.services.user_profile_service._build_export_payload",
            new=AsyncMock(return_value=fake_payload),
        ):
            result = await UserProfileService._process_export(
                db, export_request=export, user_id=user_id,
            )

        assert result["status"] == "failed"
        assert export.status == ExportStatus.FAILED.value
        assert export.error_message is not None
        assert "maximum size" in export.error_message

    async def test_sets_processing_status_before_building(self) -> None:
        """Status is flipped to PROCESSING before payload build runs."""
        user_id = uuid.uuid4()
        export = _make_export(user_id, status=ExportStatus.PENDING.value)
        db = _make_db()

        observed_status: list[str] = []

        async def fake_builder(
            _db: Any, *, user_id: uuid.UUID, export_type: str,
        ) -> dict[str, Any]:
            observed_status.append(export.status)
            return {
                "metadata": {},
                "manifest": {"total_records": 0, "categories": {}},
                "data": {},
            }

        with patch(
            "app.services.user_profile_service._build_export_payload",
            new=fake_builder,
        ):
            await UserProfileService._process_export(
                db, export_request=export, user_id=user_id,
            )

        assert observed_status == [ExportStatus.PROCESSING.value]
        assert export.status == ExportStatus.COMPLETED.value

    async def test_checksum_is_stable_for_same_payload(self) -> None:
        """SHA-256 of JSON-serialised payload is deterministic."""
        user_id = uuid.uuid4()
        export_a = _make_export(user_id)
        export_b = _make_export(user_id)
        db = _make_db()

        fake_payload: dict[str, Any] = {
            "metadata": {"user_id": str(user_id)},
            "manifest": {"total_records": 0, "categories": {}},
            "data": {},
        }

        with patch(
            "app.services.user_profile_service._build_export_payload",
            new=AsyncMock(return_value=fake_payload),
        ):
            await UserProfileService._process_export(
                db, export_request=export_a, user_id=user_id,
            )
            await UserProfileService._process_export(
                db, export_request=export_b, user_id=user_id,
            )

        assert export_a.checksum == export_b.checksum
