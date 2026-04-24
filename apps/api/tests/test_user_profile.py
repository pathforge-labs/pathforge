"""
PathForge — User Profile & GDPR Export Test Suite
====================================================
Tests for Sprint 22: models, enums, service helpers, export payload.

Coverage:
    - StrEnum values (ExportType, ExportFormat, ExportStatus)
    - Model creation (UserProfile, DataExportRequest)
    - GDPR export payload structure
    - Export record counting
    - Schema validation (response models)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.models.user_profile import (
    DataExportRequest,
    ExportFormat,
    ExportStatus,
    ExportType,
    UserProfile,
)
from app.schemas.user_profile import (
    DataExportListResponse,
    DataExportRequestResponse,
    OnboardingStatusResponse,
    UserDataSummaryResponse,
    UserProfileResponse,
)
from app.services.user_profile_service import (
    EXPORT_EXPIRY_DAYS,
    EXPORT_RATE_LIMIT_HOURS,
    _count_export_records,
)

# ── Enum Tests ─────────────────────────────────────────────────


class TestEnums:
    """Test StrEnum definitions."""

    def test_export_type_values(self) -> None:
        assert ExportType.FULL == "full"
        assert ExportType.CAREER_DNA_ONLY == "career_dna_only"
        assert ExportType.INTELLIGENCE_ONLY == "intelligence_only"

    def test_export_format_values(self) -> None:
        assert ExportFormat.JSON == "json"

    def test_export_status_values(self) -> None:
        assert ExportStatus.PENDING == "pending"
        assert ExportStatus.PROCESSING == "processing"
        assert ExportStatus.COMPLETED == "completed"
        assert ExportStatus.FAILED == "failed"
        assert ExportStatus.EXPIRED == "expired"


# ── Model Creation Tests ──────────────────────────────────────


class TestUserProfileModel:
    """Test UserProfile model instantiation."""

    def test_create_profile(self) -> None:
        profile = UserProfile(
            user_id=str(uuid.uuid4()),
            display_name="Emre Dursun",
            headline="ISTQB® Certified Full-Stack Automation Engineer",
            bio="Building PathForge.",
            location="Netherlands",
            timezone="Europe/Amsterdam",
            language="en",
        )
        assert profile.display_name == "Emre Dursun"
        assert profile.headline == "ISTQB® Certified Full-Stack Automation Engineer"
        assert profile.timezone == "Europe/Amsterdam"
        assert profile.__tablename__ == "user_profiles"

    def test_default_onboarding_incomplete(self) -> None:
        # onboarding_completed has a column default but not an __init__ default
        # so when instantiating without DB, it may be MISSING. We test the
        # column-level default is set up correctly via __table__ inspection.
        col = UserProfile.__table__.columns["onboarding_completed"]
        assert col.default.arg is False


class TestDataExportRequestModel:
    """Test DataExportRequest model instantiation."""

    def test_create_export_request(self) -> None:
        export_request = DataExportRequest(
            user_id=str(uuid.uuid4()),
            export_type="full",
            format_="json",
            status="pending",
        )
        assert export_request.export_type == "full"
        assert export_request.format_ == "json"
        assert export_request.status == "pending"
        assert export_request.__tablename__ == "user_data_export_requests"

    def test_gdpr_fields(self) -> None:
        now = datetime.now(UTC)
        export_request = DataExportRequest(
            user_id=str(uuid.uuid4()),
            export_type="full",
            format_="json",
            status="completed",
            checksum="abc123def456",
            record_count=42,
            file_size_bytes=1024,
            completed_at=now,
            expires_at=now,
        )
        assert export_request.checksum == "abc123def456"
        assert export_request.record_count == 42
        assert export_request.file_size_bytes == 1024


# ── Export Helper Tests ───────────────────────────────────────


class TestCountExportRecords:
    """Test export record counting helper."""

    def test_counts_from_manifest(self) -> None:
        payload = {
            "manifest": {
                "total_records": 42,
                "categories": {"profile": 1, "notifications": 41},
            },
        }
        assert _count_export_records(payload) == 42

    def test_empty_manifest(self) -> None:
        payload = {"manifest": {}}
        assert _count_export_records(payload) == 0

    def test_no_manifest(self) -> None:
        payload = {}
        assert _count_export_records(payload) == 0


# ── Constants Tests ───────────────────────────────────────────


class TestConstants:
    """Test service constants are reasonable."""

    def test_rate_limit_hours(self) -> None:
        assert EXPORT_RATE_LIMIT_HOURS == 24

    def test_export_expiry_days(self) -> None:
        assert EXPORT_EXPIRY_DAYS == 7


# ── Schema Validation Tests ──────────────────────────────────


class TestSchemaValidation:
    """Test Pydantic response schemas accept model-like data."""

    def test_profile_response(self) -> None:
        now = datetime.now(UTC)
        data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "display_name": "Emre Dursun",
            "headline": "Engineer",
            "bio": "Building PathForge.",
            "location": "Netherlands",
            "timezone": "Europe/Amsterdam",
            "language": "en",
            "avatar_url": None,
            "onboarding_completed": False,
            "preferences": None,
            "created_at": now,
            "updated_at": now,
        }
        response = UserProfileResponse(**data)
        assert response.display_name == "Emre Dursun"
        assert response.timezone == "Europe/Amsterdam"

    def test_export_request_response(self) -> None:
        now = datetime.now(UTC)
        data = {
            "id": str(uuid.uuid4()),
            "user_id": str(uuid.uuid4()),
            "export_type": "full",
            "format": "json",
            "status": "completed",
            "checksum": "sha256hash",
            "record_count": 42,
            "file_size_bytes": 2048,
            "completed_at": now,
            "expires_at": now,
            "error_message": None,
            "download_count": 1,
            "last_downloaded_at": None,
            "created_at": now,
        }
        response = DataExportRequestResponse(**data)
        assert response.export_type == "full"
        assert response.record_count == 42

    def test_export_list_response(self) -> None:
        data = {
            "exports": [],
            "total": 0,
            "page": 1,
            "page_size": 20,
        }
        response = DataExportListResponse(**data)
        assert response.total == 0

    def test_onboarding_status_response(self) -> None:
        data = {
            "onboarding_completed": False,
            "profile_exists": True,
            "career_dna_exists": False,
            "engines_activated": 0,
            "total_engines": 12,
        }
        response = OnboardingStatusResponse(**data)
        assert response.profile_exists is True
        assert response.career_dna_exists is False

    def test_data_summary_response(self) -> None:
        data = {
            "total_records": 15,
            "engines": {},
            "profile_data": True,
            "notification_count": 10,
            "export_count": 4,
        }
        response = UserDataSummaryResponse(**data)
        assert response.total_records == 15


# ── Service-Layer Tests (async, DB-backed) ────────────────────

from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.user_profile_service import (
    UserProfileService,
    _build_export_payload,
)


class TestProfileCRUD:
    """Test UserProfileService create/update/delete lifecycle."""

    @pytest.mark.asyncio
    async def test_create_profile_fields(
        self, db_session: AsyncSession,
    ) -> None:
        """Create with data dict → all fields set correctly."""
        user_id = uuid.uuid4()
        profile = await UserProfileService.create_profile(
            db_session,
            user_id=user_id,
            data={
                "display_name": "Test User",
                "headline": "Software Engineer",
                "location": "Amsterdam",
                "timezone": "Europe/Amsterdam",
            },
        )
        assert profile.display_name == "Test User"
        assert profile.headline == "Software Engineer"
        assert profile.location == "Amsterdam"
        assert profile.timezone == "Europe/Amsterdam"
        assert profile.language == "en"  # Default

    @pytest.mark.asyncio
    async def test_update_profile_partial(
        self, db_session: AsyncSession,
    ) -> None:
        """Partial update preserves other fields."""
        user_id = uuid.uuid4()
        await UserProfileService.create_profile(
            db_session,
            user_id=user_id,
            data={
                "display_name": "Original",
                "headline": "Engineer",
                "location": "Amsterdam",
            },
        )
        updated = await UserProfileService.update_profile(
            db_session,
            user_id=user_id,
            updates={"headline": "Senior Engineer"},
        )
        assert updated is not None
        assert updated.headline == "Senior Engineer"
        assert updated.display_name == "Original"  # Unchanged
        assert updated.location == "Amsterdam"  # Unchanged

    @pytest.mark.asyncio
    async def test_delete_profile_returns_false_when_missing(
        self, db_session: AsyncSession,
    ) -> None:
        """Delete non-existent profile → returns False."""
        user_id = uuid.uuid4()
        result = await UserProfileService.delete_profile(
            db_session, user_id=user_id,
        )
        assert result is False


class TestOnboardingStatus:
    """Test UserProfileService.get_onboarding_status."""

    @pytest.mark.asyncio
    async def test_onboarding_no_profile(
        self, db_session: AsyncSession,
    ) -> None:
        """No profile → profile_exists=False, onboarding_completed=False."""
        user_id = uuid.uuid4()
        status = await UserProfileService.get_onboarding_status(
            db_session, user_id=user_id,
        )
        assert status["profile_exists"] is False
        assert status["onboarding_completed"] is False
        assert status["total_engines"] == 12

    @pytest.mark.asyncio
    async def test_onboarding_with_profile(
        self, db_session: AsyncSession,
    ) -> None:
        """Profile exists → profile_exists=True, reflects profile data."""
        user_id = uuid.uuid4()
        await UserProfileService.create_profile(
            db_session,
            user_id=user_id,
            data={"display_name": "Onboarding User"},
        )
        status = await UserProfileService.get_onboarding_status(
            db_session, user_id=user_id,
        )
        assert status["profile_exists"] is True
        assert status["career_dna_exists"] is False


class TestExportPipeline:
    """Test _build_export_payload GDPR structure."""

    @pytest.mark.asyncio
    async def test_export_payload_structure(
        self, db_session: AsyncSession,
    ) -> None:
        """Payload has all required top-level keys."""
        user_id = uuid.uuid4()
        payload = await _build_export_payload(
            db_session, user_id=user_id, export_type="full",
        )
        assert "metadata" in payload
        assert "ai_methodology_disclosure" in payload
        assert "manifest" in payload
        assert "data" in payload
        assert payload["metadata"]["export_type"] == "full"
        assert payload["metadata"]["gdpr_article"] == (
            "Article 20 — Right to Data Portability"
        )

    @pytest.mark.asyncio
    async def test_export_payload_ai_disclosure(
        self, db_session: AsyncSession,
    ) -> None:
        """AI disclosure has transparency_policy and engines list."""
        user_id = uuid.uuid4()
        payload = await _build_export_payload(
            db_session, user_id=user_id, export_type="full",
        )
        disclosure = payload["ai_methodology_disclosure"]
        assert "transparency_policy" in disclosure
        assert "engines" in disclosure
        assert isinstance(disclosure["engines"], list)
        assert len(disclosure["engines"]) > 0
        # Each engine should have confidence_cap
        first_engine = disclosure["engines"][0]
        assert first_engine["confidence_cap"] == 0.85

    @pytest.mark.asyncio
    async def test_export_payload_manifest_counts(
        self, db_session: AsyncSession,
    ) -> None:
        """Manifest total_records matches actual data categories."""
        user_id = uuid.uuid4()
        # Create a profile so we have at least one record
        await UserProfileService.create_profile(
            db_session,
            user_id=user_id,
            data={"display_name": "Export Test"},
        )
        payload = await _build_export_payload(
            db_session, user_id=user_id, export_type="full",
        )
        manifest = payload["manifest"]
        assert manifest["total_records"] >= 1
        assert "profile" in manifest["categories"]
        assert manifest["categories"]["profile"] == 1


_MOCK_BG = "app.services.user_profile_service._process_export_background"


class TestExportRateLimiting:
    """Test UserProfileService.request_export rate limiting."""

    @pytest.mark.asyncio
    async def test_export_rate_limited(
        self, db_session: AsyncSession,
    ) -> None:
        """Second export within 24h → rate_limited status."""
        user_id = uuid.uuid4()
        with patch(_MOCK_BG, new=AsyncMock()):
            # First export
            first_result = await UserProfileService.request_export(
                db_session, user_id=user_id,
            )
            assert first_result.get("status") != "rate_limited"
            # Second export (should be rate limited)
            second_result = await UserProfileService.request_export(
                db_session, user_id=user_id,
            )
        assert second_result["status"] == "rate_limited"

    @pytest.mark.asyncio
    async def test_export_allowed_after_window(
        self, db_session: AsyncSession,
    ) -> None:
        """No recent export → proceeds normally."""
        user_id = uuid.uuid4()
        with patch(_MOCK_BG, new=AsyncMock()):
            result = await UserProfileService.request_export(
                db_session, user_id=user_id,
            )
        # First request should always succeed (may return processing or completed)
        assert result.get("status") in {"processing", "completed"}
        assert "export_id" in result
