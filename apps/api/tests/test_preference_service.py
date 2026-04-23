"""
PathForge — Preference & Blacklist Service Unit Tests
=======================================================
Service-layer tests for preference_service.py.
Uses real in-memory SQLite fixture — no mocks needed (pure DB logic).

Coverage targets:
    - PreferenceService.get_by_user (existing, missing)
    - PreferenceService.upsert (create, update)
    - BlacklistService.get_by_user (empty, populated)
    - BlacklistService.add
    - BlacklistService.remove (found, not found, wrong user)
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.preference_service import BlacklistService, PreferenceService

# ── Fixtures ──────────────────────────────────────────────────────


async def _make_user(db: AsyncSession, email: str) -> User:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Pref Tester",
    )
    db.add(user)
    await db.flush()
    return user


# ── PreferenceService ─────────────────────────────────────────────


class TestPreferenceService:
    @pytest.mark.asyncio
    async def test_get_by_user_returns_none_when_no_preference(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="pref-none@test.com")
        result = await PreferenceService.get_by_user(db_session, user.id)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_creates_preference_on_first_call(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="pref-create@test.com")
        pref = await PreferenceService.upsert(
            db_session, user.id, work_type="remote",
        )
        assert pref.id is not None
        assert pref.user_id == user.id
        assert pref.work_type == "remote"

    @pytest.mark.asyncio
    async def test_upsert_returns_same_record_on_second_call(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="pref-idem@test.com")
        pref1 = await PreferenceService.upsert(db_session, user.id)
        pref2 = await PreferenceService.upsert(db_session, user.id)
        assert pref1.id == pref2.id

    @pytest.mark.asyncio
    async def test_upsert_updates_existing_preference(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="pref-update@test.com")
        await PreferenceService.upsert(
            db_session, user.id, salary_min=50000,
        )
        updated = await PreferenceService.upsert(
            db_session, user.id, salary_min=65000,
        )
        assert updated.salary_min == 65000

    @pytest.mark.asyncio
    async def test_upsert_skips_none_values(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="pref-skip-none@test.com")
        await PreferenceService.upsert(
            db_session, user.id, work_type="hybrid",
        )
        # Passing None should not overwrite existing value
        updated = await PreferenceService.upsert(
            db_session, user.id, work_type=None,
        )
        assert updated.work_type == "hybrid"

    @pytest.mark.asyncio
    async def test_get_by_user_returns_preference_after_upsert(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="pref-get@test.com")
        await PreferenceService.upsert(
            db_session, user.id, experience_level="senior",
        )
        fetched = await PreferenceService.get_by_user(db_session, user.id)
        assert fetched is not None
        assert fetched.experience_level == "senior"


# ── BlacklistService ──────────────────────────────────────────────


class TestBlacklistService:
    @pytest.mark.asyncio
    async def test_get_by_user_returns_empty_list_when_no_entries(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-empty@test.com")
        result = await BlacklistService.get_by_user(db_session, user.id)
        assert result == []

    @pytest.mark.asyncio
    async def test_add_creates_blacklist_entry(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-add@test.com")
        entry = await BlacklistService.add(
            db_session,
            user_id=user.id,
            company_name="Evil Corp",
            reason="Bad culture",
        )
        assert entry.id is not None
        assert entry.company_name == "Evil Corp"
        assert entry.reason == "Bad culture"
        assert entry.is_current_employer is False

    @pytest.mark.asyncio
    async def test_add_with_is_current_employer_flag(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-current@test.com")
        entry = await BlacklistService.add(
            db_session,
            user_id=user.id,
            company_name="CurrentCo",
            is_current_employer=True,
        )
        assert entry.is_current_employer is True

    @pytest.mark.asyncio
    async def test_get_by_user_returns_all_entries(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-list@test.com")
        for name in ["Company A", "Company B", "Company C"]:
            await BlacklistService.add(
                db_session, user_id=user.id, company_name=name,
            )
        entries = await BlacklistService.get_by_user(db_session, user.id)
        assert len(entries) == 3

    @pytest.mark.asyncio
    async def test_remove_returns_true_and_deletes_entry(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-remove@test.com")
        entry = await BlacklistService.add(
            db_session, user_id=user.id, company_name="ToDelete",
        )
        result = await BlacklistService.remove(
            db_session, entry_id=entry.id, user_id=user.id,
        )
        assert result is True

        remaining = await BlacklistService.get_by_user(db_session, user.id)
        assert all(e.id != entry.id for e in remaining)

    @pytest.mark.asyncio
    async def test_remove_returns_false_when_entry_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-notfound@test.com")
        result = await BlacklistService.remove(
            db_session, entry_id=uuid.uuid4(), user_id=user.id,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_remove_returns_false_for_wrong_user(
        self, db_session: AsyncSession,
    ) -> None:
        owner = await _make_user(db_session, email="bl-owner@test.com")
        other = await _make_user(db_session, email="bl-other@test.com")
        entry = await BlacklistService.add(
            db_session, user_id=owner.id, company_name="OwnersCo",
        )
        result = await BlacklistService.remove(
            db_session, entry_id=entry.id, user_id=other.id,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_entries_are_isolated_per_user(
        self, db_session: AsyncSession,
    ) -> None:
        user1 = await _make_user(db_session, email="bl-user1@test.com")
        user2 = await _make_user(db_session, email="bl-user2@test.com")
        await BlacklistService.add(
            db_session, user_id=user1.id, company_name="User1Corp",
        )
        entries_user2 = await BlacklistService.get_by_user(db_session, user2.id)
        assert entries_user2 == []
