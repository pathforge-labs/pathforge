"""
PathForge — Application Service Unit Tests
===========================================
Service-layer tests for application_service.py.
Uses real in-memory SQLite fixture — no mocks needed (pure DB logic).

Coverage targets:
    - check_blacklist (hit, miss, case-insensitivity, whitespace)
    - check_rate_limit (hourly, daily, SAVED excluded)
    - create_application (success, blacklist, rate limit, not found)
    - get_application (found, not found, wrong user)
    - list_applications (empty, pagination, status filter)
    - update_status (valid, invalid transition, not found, applied rate limit)
    - delete_application (success, not found)
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application, ApplicationStatus
from app.models.matching import JobListing
from app.models.preference import BlacklistEntry
from app.models.user import User
from app.services import application_service
from app.services.application_service import (
    ApplicationError,
    BlacklistViolation,
    InvalidTransition,
    RateLimitViolation,
    check_blacklist,
    check_rate_limit,
    create_application,
    delete_application,
    get_application,
    list_applications,
    update_status,
)

# ── Helpers ───────────────────────────────────────────────────────


async def _make_user(db: AsyncSession, email: str) -> User:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="App Tester",
    )
    db.add(user)
    await db.flush()
    return user


async def _make_job(
    db: AsyncSession,
    *,
    title: str = "Senior Engineer",
    company: str = "Acme Corp",
    source_url: str | None = "https://example.com/job/1",
) -> JobListing:
    job = JobListing(
        title=title,
        company=company,
        description="A great job",
        source_url=source_url,
    )
    db.add(job)
    await db.flush()
    return job


async def _make_blacklist(
    db: AsyncSession, user_id: uuid.UUID, company: str,
) -> BlacklistEntry:
    entry = BlacklistEntry(user_id=user_id, company_name=company)
    db.add(entry)
    await db.flush()
    return entry


# ── Error class ───────────────────────────────────────────────────


class TestErrorClasses:
    def test_application_error_stores_message_and_code(self) -> None:
        err = ApplicationError("boom", code="OOPS")
        assert err.message == "boom"
        assert err.code == "OOPS"
        assert str(err) == "boom"

    def test_application_error_default_code(self) -> None:
        err = ApplicationError("oops")
        assert err.code == "APPLICATION_ERROR"

    def test_blacklist_violation_sets_code(self) -> None:
        err = BlacklistViolation("Evil Corp")
        assert err.code == "BLACKLIST_VIOLATION"
        assert "Evil Corp" in err.message

    def test_rate_limit_violation_sets_code(self) -> None:
        err = RateLimitViolation("hour", 10)
        assert err.code == "RATE_LIMIT_EXCEEDED"
        assert "10" in err.message
        assert "hour" in err.message

    def test_invalid_transition_sets_code(self) -> None:
        err = InvalidTransition("saved", "offered")
        assert err.code == "INVALID_TRANSITION"


# ── check_blacklist ───────────────────────────────────────────────


class TestCheckBlacklist:
    @pytest.mark.asyncio
    async def test_passes_when_not_blacklisted(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-none@test.com")
        # Should not raise
        await check_blacklist(db_session, user.id, "Acme Corp")

    @pytest.mark.asyncio
    async def test_raises_when_blacklisted(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-hit@test.com")
        await _make_blacklist(db_session, user.id, "Evil Corp")
        with pytest.raises(BlacklistViolation):
            await check_blacklist(db_session, user.id, "Evil Corp")

    @pytest.mark.asyncio
    async def test_matches_case_insensitively(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-case@test.com")
        await _make_blacklist(db_session, user.id, "Evil Corp")
        with pytest.raises(BlacklistViolation):
            await check_blacklist(db_session, user.id, "eVil cOrp")

    @pytest.mark.asyncio
    async def test_strips_whitespace(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="bl-ws@test.com")
        await _make_blacklist(db_session, user.id, "Evil Corp")
        with pytest.raises(BlacklistViolation):
            await check_blacklist(db_session, user.id, "  Evil Corp  ")


# ── check_rate_limit ──────────────────────────────────────────────


class TestCheckRateLimit:
    @pytest.mark.asyncio
    async def test_passes_with_no_applications(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="rl-empty@test.com")
        # Should not raise
        await check_rate_limit(db_session, user.id)

    @pytest.mark.asyncio
    async def test_saved_applications_do_not_count(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="rl-saved@test.com")
        for _ in range(15):
            job = await _make_job(
                db_session, company=f"Co{uuid.uuid4().hex[:6]}",
            )
            db_session.add(
                Application(
                    user_id=user.id,
                    job_listing_id=job.id,
                    status=ApplicationStatus.SAVED,
                ),
            )
        await db_session.flush()
        # Should still pass — SAVED applications are excluded
        await check_rate_limit(db_session, user.id)

    @pytest.mark.asyncio
    async def test_raises_at_hourly_limit(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="rl-hour@test.com")
        for _ in range(application_service.RATE_LIMIT_HOURLY):
            job = await _make_job(
                db_session, company=f"Co{uuid.uuid4().hex[:6]}",
            )
            db_session.add(
                Application(
                    user_id=user.id,
                    job_listing_id=job.id,
                    status=ApplicationStatus.APPLIED,
                ),
            )
        await db_session.flush()
        with pytest.raises(RateLimitViolation) as exc:
            await check_rate_limit(db_session, user.id)
        assert "hour" in exc.value.message

    @pytest.mark.asyncio
    async def test_raises_at_daily_limit(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="rl-day@test.com")
        # Insert hourly-limit applications more than 1h ago but within 24h
        old_time = datetime.now(UTC) - timedelta(hours=2)
        for _ in range(application_service.RATE_LIMIT_DAILY):
            job = await _make_job(
                db_session, company=f"Co{uuid.uuid4().hex[:6]}",
            )
            app = Application(
                user_id=user.id,
                job_listing_id=job.id,
                status=ApplicationStatus.APPLIED,
            )
            app.created_at = old_time
            db_session.add(app)
        await db_session.flush()
        with pytest.raises(RateLimitViolation) as exc:
            await check_rate_limit(db_session, user.id)
        assert "day" in exc.value.message


# ── create_application ────────────────────────────────────────────


class TestCreateApplication:
    @pytest.mark.asyncio
    async def test_create_saved_application_success(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="create-save@test.com")
        job = await _make_job(db_session)
        app = await create_application(db_session, user.id, job.id)
        assert app.id is not None
        assert app.user_id == user.id
        assert app.job_listing_id == job.id
        assert app.status == ApplicationStatus.SAVED
        assert app.source_url == job.source_url

    @pytest.mark.asyncio
    async def test_create_applied_with_notes(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="create-applied@test.com")
        job = await _make_job(db_session)
        app = await create_application(
            db_session,
            user.id,
            job.id,
            status=ApplicationStatus.APPLIED,
            notes="Applied via referral",
        )
        assert app.status == ApplicationStatus.APPLIED
        assert app.notes == "Applied via referral"

    @pytest.mark.asyncio
    async def test_create_raises_when_job_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="create-nojob@test.com")
        with pytest.raises(ApplicationError) as exc:
            await create_application(db_session, user.id, uuid.uuid4())
        assert exc.value.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_create_raises_on_blacklisted_company(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="create-bl@test.com")
        job = await _make_job(db_session, company="Evil Corp")
        await _make_blacklist(db_session, user.id, "Evil Corp")
        with pytest.raises(BlacklistViolation):
            await create_application(db_session, user.id, job.id)

    @pytest.mark.asyncio
    async def test_create_applied_enforces_rate_limit(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="create-rl@test.com")
        # Fill up hourly quota
        for _ in range(application_service.RATE_LIMIT_HOURLY):
            job = await _make_job(
                db_session, company=f"Co{uuid.uuid4().hex[:6]}",
            )
            db_session.add(
                Application(
                    user_id=user.id,
                    job_listing_id=job.id,
                    status=ApplicationStatus.APPLIED,
                ),
            )
        await db_session.flush()
        new_job = await _make_job(db_session, company="NewCo")
        with pytest.raises(RateLimitViolation):
            await create_application(
                db_session,
                user.id,
                new_job.id,
                status=ApplicationStatus.APPLIED,
            )


# ── get_application ───────────────────────────────────────────────


class TestGetApplication:
    @pytest.mark.asyncio
    async def test_returns_application_for_owner(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="get-owner@test.com")
        job = await _make_job(db_session)
        app = await create_application(db_session, user.id, job.id)
        fetched = await get_application(db_session, app.id, user.id)
        assert fetched is not None
        assert fetched.id == app.id

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="get-missing@test.com")
        fetched = await get_application(db_session, uuid.uuid4(), user.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_returns_none_for_wrong_user(
        self, db_session: AsyncSession,
    ) -> None:
        owner = await _make_user(db_session, email="get-a@test.com")
        other = await _make_user(db_session, email="get-b@test.com")
        job = await _make_job(db_session)
        app = await create_application(db_session, owner.id, job.id)
        fetched = await get_application(db_session, app.id, other.id)
        assert fetched is None


# ── list_applications ─────────────────────────────────────────────


class TestListApplications:
    @pytest.mark.asyncio
    async def test_empty_list_returns_zero_total(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="list-empty@test.com")
        apps, total = await list_applications(db_session, user.id)
        assert apps == []
        assert total == 0

    @pytest.mark.asyncio
    async def test_returns_only_owners_applications(
        self, db_session: AsyncSession,
    ) -> None:
        owner = await _make_user(db_session, email="list-owner@test.com")
        other = await _make_user(db_session, email="list-other@test.com")
        job_a = await _make_job(db_session, company="A")
        job_b = await _make_job(db_session, company="B")
        await create_application(db_session, owner.id, job_a.id)
        await create_application(db_session, other.id, job_b.id)
        apps, total = await list_applications(db_session, owner.id)
        assert total == 1
        assert len(apps) == 1
        assert apps[0].user_id == owner.id

    @pytest.mark.asyncio
    async def test_status_filter(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="list-filter@test.com")
        job1 = await _make_job(db_session, company="Co1")
        job2 = await _make_job(db_session, company="Co2")
        await create_application(db_session, user.id, job1.id)
        await create_application(
            db_session,
            user.id,
            job2.id,
            status=ApplicationStatus.APPLIED,
        )
        apps, total = await list_applications(
            db_session, user.id, status_filter=ApplicationStatus.APPLIED,
        )
        assert total == 1
        assert apps[0].status == ApplicationStatus.APPLIED

    @pytest.mark.asyncio
    async def test_pagination_limits_results(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="list-page@test.com")
        for i in range(5):
            job = await _make_job(db_session, company=f"C{i}")
            await create_application(db_session, user.id, job.id)
        apps, total = await list_applications(
            db_session, user.id, page=1, per_page=2,
        )
        assert total == 5
        assert len(apps) == 2

    @pytest.mark.asyncio
    async def test_pagination_second_page(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="list-page2@test.com")
        for i in range(5):
            job = await _make_job(db_session, company=f"D{i}")
            await create_application(db_session, user.id, job.id)
        apps, total = await list_applications(
            db_session, user.id, page=2, per_page=2,
        )
        assert total == 5
        assert len(apps) == 2


# ── update_status ─────────────────────────────────────────────────


class TestUpdateStatus:
    @pytest.mark.asyncio
    async def test_valid_transition_saved_to_applied(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="upd-valid@test.com")
        job = await _make_job(db_session)
        app = await create_application(db_session, user.id, job.id)
        updated = await update_status(
            db_session, app.id, user.id, ApplicationStatus.APPLIED,
        )
        assert updated.status == ApplicationStatus.APPLIED

    @pytest.mark.asyncio
    async def test_invalid_transition_raises(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="upd-invalid@test.com")
        job = await _make_job(db_session)
        app = await create_application(db_session, user.id, job.id)
        with pytest.raises(InvalidTransition):
            await update_status(
                db_session, app.id, user.id, ApplicationStatus.OFFERED,
            )

    @pytest.mark.asyncio
    async def test_update_raises_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="upd-missing@test.com")
        with pytest.raises(ApplicationError) as exc:
            await update_status(
                db_session,
                uuid.uuid4(),
                user.id,
                ApplicationStatus.APPLIED,
            )
        assert exc.value.code == "NOT_FOUND"

    @pytest.mark.asyncio
    async def test_update_to_applied_enforces_rate_limit(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="upd-rl@test.com")
        # Fill hourly quota with APPLIED entries
        for _ in range(application_service.RATE_LIMIT_HOURLY):
            qjob = await _make_job(
                db_session, company=f"Co{uuid.uuid4().hex[:6]}",
            )
            db_session.add(
                Application(
                    user_id=user.id,
                    job_listing_id=qjob.id,
                    status=ApplicationStatus.APPLIED,
                ),
            )
        await db_session.flush()
        # A SAVED app we try to transition
        new_job = await _make_job(db_session, company="TargetCo")
        saved_app = await create_application(
            db_session, user.id, new_job.id,
        )
        with pytest.raises(RateLimitViolation):
            await update_status(
                db_session,
                saved_app.id,
                user.id,
                ApplicationStatus.APPLIED,
            )

    @pytest.mark.asyncio
    async def test_terminal_state_rejects_all_transitions(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="upd-terminal@test.com")
        job = await _make_job(db_session)
        # Force create a REJECTED app directly to test terminal state
        app = Application(
            user_id=user.id,
            job_listing_id=job.id,
            status=ApplicationStatus.REJECTED,
        )
        db_session.add(app)
        await db_session.flush()
        with pytest.raises(InvalidTransition):
            await update_status(
                db_session, app.id, user.id, ApplicationStatus.APPLIED,
            )


# ── delete_application ────────────────────────────────────────────


class TestDeleteApplication:
    @pytest.mark.asyncio
    async def test_delete_returns_true_when_found(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="del-ok@test.com")
        job = await _make_job(db_session)
        app = await create_application(db_session, user.id, job.id)
        result = await delete_application(db_session, app.id, user.id)
        assert result is True
        fetched = await get_application(db_session, app.id, user.id)
        assert fetched is None

    @pytest.mark.asyncio
    async def test_delete_returns_false_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, email="del-missing@test.com")
        result = await delete_application(
            db_session, uuid.uuid4(), user.id,
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_delete_returns_false_for_wrong_user(
        self, db_session: AsyncSession,
    ) -> None:
        owner = await _make_user(db_session, email="del-owner@test.com")
        other = await _make_user(db_session, email="del-other@test.com")
        job = await _make_job(db_session)
        app = await create_application(db_session, owner.id, job.id)
        result = await delete_application(db_session, app.id, other.id)
        assert result is False
        # Still exists for owner
        fetched = await get_application(db_session, app.id, owner.id)
        assert fetched is not None
