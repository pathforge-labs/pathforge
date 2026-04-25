"""Unit tests for ResumeService — direct DB session, covers all branches."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.resume_service import ResumeService


async def _make_user(db_session: AsyncSession, email: str = "resume@example.com") -> User:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("pass"),
        full_name="Resume User",
    )
    db_session.add(user)
    await db_session.flush()
    return user


# ── create ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_create_first_resume_version_1(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)
    resume = await ResumeService.create(
        db_session, user_id=user.id, title="My CV", raw_text="Experience...",
    )
    assert resume.version == 1
    assert resume.title == "My CV"
    assert resume.raw_text == "Experience..."
    assert resume.user_id == user.id


@pytest.mark.asyncio
async def test_create_second_resume_increments_version(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "v2@example.com")
    await ResumeService.create(db_session, user_id=user.id)
    v2 = await ResumeService.create(db_session, user_id=user.id, title="V2")
    assert v2.version == 2


@pytest.mark.asyncio
async def test_create_with_file_url(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "fileurl@example.com")
    resume = await ResumeService.create(
        db_session,
        user_id=user.id,
        file_url="https://storage.example.com/resume.pdf",
    )
    assert resume.file_url == "https://storage.example.com/resume.pdf"
    assert resume.version == 1


# ── get_by_user ───────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_user_empty(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "empty@example.com")
    resumes = await ResumeService.get_by_user(db_session, user.id)
    assert resumes == []


@pytest.mark.asyncio
async def test_get_by_user_multiple_ordered_desc(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "multi@example.com")
    await ResumeService.create(db_session, user_id=user.id, title="V1")
    await ResumeService.create(db_session, user_id=user.id, title="V2")
    resumes = await ResumeService.get_by_user(db_session, user.id)
    assert len(resumes) == 2
    assert resumes[0].version > resumes[1].version


# ── get_by_id ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_get_by_id_found(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "getbyid@example.com")
    created = await ResumeService.create(db_session, user_id=user.id)
    found = await ResumeService.get_by_id(db_session, created.id, user.id)
    assert found is not None
    assert found.id == created.id


@pytest.mark.asyncio
async def test_get_by_id_wrong_user_returns_none(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "owner@example.com")
    other_user = await _make_user(db_session, "other@example.com")
    created = await ResumeService.create(db_session, user_id=user.id)
    found = await ResumeService.get_by_id(db_session, created.id, other_user.id)
    assert found is None


@pytest.mark.asyncio
async def test_get_by_id_not_found(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "notfound@example.com")
    found = await ResumeService.get_by_id(db_session, uuid.uuid4(), user.id)
    assert found is None


# ── delete ────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_delete_existing_resume(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "delete@example.com")
    resume = await ResumeService.create(db_session, user_id=user.id)
    deleted = await ResumeService.delete(db_session, resume.id, user.id)
    assert deleted is True
    found = await ResumeService.get_by_id(db_session, resume.id, user.id)
    assert found is None


@pytest.mark.asyncio
async def test_delete_nonexistent_returns_false(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, "delnone@example.com")
    deleted = await ResumeService.delete(db_session, uuid.uuid4(), user.id)
    assert deleted is False
