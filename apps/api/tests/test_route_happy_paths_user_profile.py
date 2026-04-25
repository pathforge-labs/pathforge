"""
PathForge — User Profile & GDPR Export Route Tests
=====================================================
Happy-path and error-path coverage for app/api/v1/user_profile.py.
Service calls are mocked; route handler bodies and exception branches
are exercised via the public API.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────────────────────


async def _make_user(db: AsyncSession, email: str) -> User:
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name="Test",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def _auth(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


def _now() -> datetime:
    return datetime.now(UTC)


# ── ORM-shaped Mock Factories ─────────────────────────────────────────────────


def _orm_user_profile() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.user_id = uuid.uuid4()
    obj.display_name = "Test User"
    obj.headline = "Software Engineer"
    obj.bio = "Bio here"
    obj.location = "Berlin, DE"
    obj.timezone = "Europe/Berlin"
    obj.language = "en"
    obj.avatar_url = None
    obj.onboarding_completed = True
    obj.preferences = None
    obj.created_at = _now()
    obj.updated_at = _now()
    return obj


def _orm_export_request() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.user_id = uuid.uuid4()
    obj.export_type = "full"
    obj.format_ = "json"
    obj.format = "json"  # alias for serialization
    obj.status = "completed"
    obj.file_size_bytes = 1024
    obj.checksum = "abc123"
    obj.record_count = 42
    obj.categories = None
    obj.expires_at = _now()
    obj.completed_at = _now()
    obj.error_message = None
    obj.download_count = 0
    obj.last_downloaded_at = None
    obj.created_at = _now()
    return obj


# ═══════════════════════════════════════════════════════════════════════════════
# Profile CRUD
# ═══════════════════════════════════════════════════════════════════════════════


class TestUserProfileCRUD:
    """GET / POST / PUT / DELETE /user-profile/profile."""

    async def test_get_profile_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-get@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.get_profile",
            new_callable=AsyncMock,
            return_value=_orm_user_profile(),
        ):
            resp = await client.get(
                "/api/v1/user-profile/profile", headers=_auth(user)
            )
        assert resp.status_code == 200

    async def test_get_profile_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-get-404@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.get_profile",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                "/api/v1/user-profile/profile", headers=_auth(user)
            )
        assert resp.status_code == 404

    async def test_create_profile_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-create@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.get_profile",
            new_callable=AsyncMock,
            return_value=None,
        ), patch(
            "app.api.v1.user_profile.UserProfileService.create_profile",
            new_callable=AsyncMock,
            return_value=_orm_user_profile(),
        ):
            resp = await client.post(
                "/api/v1/user-profile/profile",
                headers=_auth(user),
                json={"display_name": "New User", "headline": "Engineer"},
            )
        assert resp.status_code == 201

    async def test_create_profile_409_when_exists(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-create-dup@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.get_profile",
            new_callable=AsyncMock,
            return_value=_orm_user_profile(),
        ):
            resp = await client.post(
                "/api/v1/user-profile/profile",
                headers=_auth(user),
                json={"display_name": "Dup"},
            )
        assert resp.status_code == 409

    async def test_update_profile_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-update@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.update_profile",
            new_callable=AsyncMock,
            return_value=_orm_user_profile(),
        ):
            resp = await client.put(
                "/api/v1/user-profile/profile",
                headers=_auth(user),
                json={"display_name": "Updated"},
            )
        assert resp.status_code == 200

    async def test_update_profile_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-update-404@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.update_profile",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.put(
                "/api/v1/user-profile/profile",
                headers=_auth(user),
                json={"display_name": "Nope"},
            )
        assert resp.status_code == 404

    async def test_delete_profile_returns_204(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-delete@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.delete_profile",
            new_callable=AsyncMock,
            return_value=True,
        ):
            resp = await client.delete(
                "/api/v1/user-profile/profile", headers=_auth(user)
            )
        assert resp.status_code == 204

    async def test_delete_profile_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-delete-404@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.delete_profile",
            new_callable=AsyncMock,
            return_value=False,
        ):
            resp = await client.delete(
                "/api/v1/user-profile/profile", headers=_auth(user)
            )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Onboarding & Data Summary
# ═══════════════════════════════════════════════════════════════════════════════


class TestOnboardingAndDataSummary:
    """GET /onboarding-status, GET /data-summary."""

    async def test_onboarding_status_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-onb@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.get_onboarding_status",
            new_callable=AsyncMock,
            return_value={
                "onboarding_completed": True,
                "profile_exists": True,
                "career_dna_exists": True,
                "engines_activated": 5,
                "total_engines": 12,
            },
        ):
            resp = await client.get(
                "/api/v1/user-profile/onboarding-status",
                headers=_auth(user),
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["onboarding_completed"] is True
        assert body["engines_activated"] == 5

    async def test_data_summary_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-summary@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.get_data_summary",
            new_callable=AsyncMock,
            return_value={
                "total_records": 100,
                "engines": {"career_dna": 1, "salary": 5},
                "profile_data": True,
                "notification_count": 10,
                "export_count": 1,
            },
        ):
            resp = await client.get(
                "/api/v1/user-profile/data-summary", headers=_auth(user)
            )
        assert resp.status_code == 200
        body = resp.json()
        assert body["total_records"] == 100


# ═══════════════════════════════════════════════════════════════════════════════
# GDPR Exports
# ═══════════════════════════════════════════════════════════════════════════════


class TestGDPRExports:
    """POST / GET /exports, GET /exports/{id}."""

    async def test_request_export_success_returns_201(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-exp@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.request_export",
            new_callable=AsyncMock,
            return_value={
                "status": "completed",
                "export_id": str(uuid.uuid4()),
                "checksum": "sha256:abc",
            },
        ):
            resp = await client.post(
                "/api/v1/user-profile/exports",
                headers=_auth(user),
                json={"export_type": "full", "format": "json"},
            )
        assert resp.status_code == 201
        assert resp.json()["status"] == "completed"

    async def test_request_export_rate_limited_returns_429(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-exp-rl@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.request_export",
            new_callable=AsyncMock,
            return_value={
                "status": "rate_limited",
                "detail": "Only one export per 24 hours.",
            },
        ):
            resp = await client.post(
                "/api/v1/user-profile/exports",
                headers=_auth(user),
                json={"export_type": "full", "format": "json"},
            )
        assert resp.status_code == 429

    async def test_request_export_failed_returns_500(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-exp-err@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.request_export",
            new_callable=AsyncMock,
            return_value={"status": "failed", "detail": "Internal error."},
        ):
            resp = await client.post(
                "/api/v1/user-profile/exports",
                headers=_auth(user),
                json={"export_type": "full", "format": "json"},
            )
        assert resp.status_code == 500

    async def test_list_exports_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-exp-list@example.com")
        await db_session.commit()
        with patch(
            "app.api.v1.user_profile.UserProfileService.list_exports",
            new_callable=AsyncMock,
            return_value={
                "exports": [],
                "total": 0,
                "page": 1,
                "page_size": 20,
            },
        ):
            resp = await client.get(
                "/api/v1/user-profile/exports", headers=_auth(user)
            )
        assert resp.status_code == 200

    async def test_get_export_status_returns_200(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-exp-status@example.com")
        await db_session.commit()
        export_id = uuid.uuid4()
        with patch(
            "app.api.v1.user_profile.UserProfileService.get_export_status",
            new_callable=AsyncMock,
            return_value=_orm_export_request(),
        ):
            resp = await client.get(
                f"/api/v1/user-profile/exports/{export_id}",
                headers=_auth(user),
            )
        assert resp.status_code == 200

    async def test_get_export_status_404_when_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        user = await _make_user(db_session, "up-exp-status-404@example.com")
        await db_session.commit()
        export_id = uuid.uuid4()
        with patch(
            "app.api.v1.user_profile.UserProfileService.get_export_status",
            new_callable=AsyncMock,
            return_value=None,
        ):
            resp = await client.get(
                f"/api/v1/user-profile/exports/{export_id}",
                headers=_auth(user),
            )
        assert resp.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# Auth requirement
# ═══════════════════════════════════════════════════════════════════════════════


class TestAuthRequired:
    async def test_profile_requires_auth(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/user-profile/profile")
        assert resp.status_code == 401
