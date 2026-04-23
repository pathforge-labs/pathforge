"""
PathForge API — WaitlistService Unit Tests
=============================================
Sprint 34: Direct service-layer tests for WaitlistService covering
all branches of join_waitlist, get_position, invite_batch,
convert_by_token, convert_by_email, get_stats, and list_entries.

Uses the real SQLite in-memory ``db_session`` fixture so we exercise
the actual SQLAlchemy query paths rather than mocks.
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.models.waitlist import WaitlistStatus
from app.services.waitlist_service import WaitlistService


def _make_user(email: str) -> User:
    """Create a minimal User ORM instance for linking tests."""
    return User(
        email=email,
        hashed_password="x",
        full_name="Linked User",
        role="user",
    )


# ─── join_waitlist ───────────────────────────────────────────────


@pytest.mark.asyncio
async def test_join_waitlist_new_entry_returns_position_one(
    db_session: AsyncSession,
) -> None:
    entry = await WaitlistService.join_waitlist(db_session, email="alice@example.com")

    assert entry.email == "alice@example.com"
    assert entry.position == 1
    assert entry.status == WaitlistStatus.PENDING.value
    assert entry.full_name is None
    assert entry.referral_source is None


@pytest.mark.asyncio
async def test_join_waitlist_normalizes_email_case_and_whitespace(
    db_session: AsyncSession,
) -> None:
    entry = await WaitlistService.join_waitlist(
        db_session, email="  MixedCase@Example.COM  "
    )
    assert entry.email == "mixedcase@example.com"


@pytest.mark.asyncio
async def test_join_waitlist_persists_full_name_and_referral(
    db_session: AsyncSession,
) -> None:
    entry = await WaitlistService.join_waitlist(
        db_session,
        email="ref@example.com",
        full_name="Referral Person",
        referral_source="twitter",
    )
    assert entry.full_name == "Referral Person"
    assert entry.referral_source == "twitter"


@pytest.mark.asyncio
async def test_join_waitlist_auto_assigns_incremental_position(
    db_session: AsyncSession,
) -> None:
    first = await WaitlistService.join_waitlist(db_session, email="one@example.com")
    second = await WaitlistService.join_waitlist(db_session, email="two@example.com")
    third = await WaitlistService.join_waitlist(db_session, email="three@example.com")

    assert first.position == 1
    assert second.position == 2
    assert third.position == 3


@pytest.mark.asyncio
async def test_join_waitlist_returns_existing_entry_when_email_duplicate(
    db_session: AsyncSession,
) -> None:
    first = await WaitlistService.join_waitlist(db_session, email="dup@example.com")
    second = await WaitlistService.join_waitlist(db_session, email="dup@example.com")

    assert second.id == first.id
    assert second.position == first.position


@pytest.mark.asyncio
async def test_join_waitlist_existing_entry_matches_after_normalization(
    db_session: AsyncSession,
) -> None:
    first = await WaitlistService.join_waitlist(db_session, email="norm@example.com")
    second = await WaitlistService.join_waitlist(
        db_session, email="   NORM@Example.com  "
    )
    assert second.id == first.id


@pytest.mark.asyncio
async def test_join_waitlist_auto_links_to_existing_user(
    db_session: AsyncSession,
) -> None:
    user = _make_user("linked@example.com")
    db_session.add(user)
    await db_session.flush()

    entry = await WaitlistService.join_waitlist(
        db_session, email="linked@example.com"
    )

    assert entry.status == WaitlistStatus.CONVERTED.value
    assert entry.converted_user_id == user.id


@pytest.mark.asyncio
async def test_join_waitlist_auto_links_when_user_email_case_differs(
    db_session: AsyncSession,
) -> None:
    user = _make_user("casey@example.com")
    db_session.add(user)
    await db_session.flush()

    entry = await WaitlistService.join_waitlist(
        db_session, email="CASEY@example.com"
    )

    assert entry.status == WaitlistStatus.CONVERTED.value
    assert entry.converted_user_id == user.id


@pytest.mark.asyncio
async def test_join_waitlist_no_autolink_when_user_absent(
    db_session: AsyncSession,
) -> None:
    entry = await WaitlistService.join_waitlist(
        db_session, email="solo@example.com"
    )
    assert entry.status == WaitlistStatus.PENDING.value
    assert entry.converted_user_id is None


# ─── get_position ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_position_returns_entry_when_found(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="find@example.com")
    entry = await WaitlistService.get_position(db_session, email="find@example.com")
    assert entry is not None
    assert entry.email == "find@example.com"


@pytest.mark.asyncio
async def test_get_position_normalizes_lookup_email(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="mixed@example.com")
    entry = await WaitlistService.get_position(
        db_session, email="  MIXED@Example.com  "
    )
    assert entry is not None
    assert entry.email == "mixed@example.com"


@pytest.mark.asyncio
async def test_get_position_returns_none_when_not_found(
    db_session: AsyncSession,
) -> None:
    entry = await WaitlistService.get_position(
        db_session, email="ghost@example.com"
    )
    assert entry is None


# ─── invite_batch ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_invite_batch_returns_empty_list_when_no_entries(
    db_session: AsyncSession,
) -> None:
    entries = await WaitlistService.invite_batch(db_session, count=5)
    assert entries == []


@pytest.mark.asyncio
async def test_invite_batch_returns_entries_in_fifo_order(
    db_session: AsyncSession,
) -> None:
    for i in range(3):
        await WaitlistService.join_waitlist(
            db_session, email=f"fifo{i}@example.com"
        )

    invited = await WaitlistService.invite_batch(db_session, count=2)

    assert len(invited) == 2
    assert invited[0].email == "fifo0@example.com"
    assert invited[1].email == "fifo1@example.com"
    assert invited[0].position < invited[1].position


@pytest.mark.asyncio
async def test_invite_batch_sets_status_and_token(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="tokentest@example.com")

    invited = await WaitlistService.invite_batch(db_session, count=1)

    assert len(invited) == 1
    assert invited[0].status == WaitlistStatus.INVITED.value
    assert invited[0].invite_token is not None
    assert len(invited[0].invite_token) > 20


@pytest.mark.asyncio
async def test_invite_batch_generates_unique_tokens(
    db_session: AsyncSession,
) -> None:
    for i in range(3):
        await WaitlistService.join_waitlist(
            db_session, email=f"uniq{i}@example.com"
        )

    invited = await WaitlistService.invite_batch(db_session, count=3)
    tokens = {e.invite_token for e in invited}
    assert len(tokens) == 3


@pytest.mark.asyncio
async def test_invite_batch_skips_already_invited_entries(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="first@example.com")
    await WaitlistService.join_waitlist(db_session, email="second@example.com")

    first_batch = await WaitlistService.invite_batch(db_session, count=1)
    second_batch = await WaitlistService.invite_batch(db_session, count=5)

    assert len(first_batch) == 1
    assert first_batch[0].email == "first@example.com"
    assert len(second_batch) == 1
    assert second_batch[0].email == "second@example.com"


@pytest.mark.asyncio
async def test_invite_batch_honors_count_limit(
    db_session: AsyncSession,
) -> None:
    for i in range(5):
        await WaitlistService.join_waitlist(
            db_session, email=f"limit{i}@example.com"
        )

    invited = await WaitlistService.invite_batch(db_session, count=2)
    assert len(invited) == 2


# ─── convert_by_token ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_convert_by_token_returns_none_when_token_missing(
    db_session: AsyncSession,
) -> None:
    entry = await WaitlistService.convert_by_token(
        db_session, invite_token="nonexistent", user_id=uuid.uuid4()
    )
    assert entry is None


@pytest.mark.asyncio
async def test_convert_by_token_success(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="convert@example.com")
    invited = await WaitlistService.invite_batch(db_session, count=1)
    token = invited[0].invite_token
    assert token is not None

    user_id = uuid.uuid4()
    entry = await WaitlistService.convert_by_token(
        db_session, invite_token=token, user_id=user_id
    )

    assert entry is not None
    assert entry.status == WaitlistStatus.CONVERTED.value
    assert entry.converted_user_id == user_id


@pytest.mark.asyncio
async def test_convert_by_token_idempotent_when_already_converted(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="idem@example.com")
    invited = await WaitlistService.invite_batch(db_session, count=1)
    token = invited[0].invite_token
    assert token is not None

    first_user = uuid.uuid4()
    first = await WaitlistService.convert_by_token(
        db_session, invite_token=token, user_id=first_user
    )
    assert first is not None

    second_user = uuid.uuid4()
    second = await WaitlistService.convert_by_token(
        db_session, invite_token=token, user_id=second_user
    )

    assert second is not None
    assert second.status == WaitlistStatus.CONVERTED.value
    # Should not overwrite the original user
    assert second.converted_user_id == first_user


# ─── convert_by_email ────────────────────────────────────────────


@pytest.mark.asyncio
async def test_convert_by_email_returns_none_when_missing(
    db_session: AsyncSession,
) -> None:
    entry = await WaitlistService.convert_by_email(
        db_session, email="missing@example.com", user_id=uuid.uuid4()
    )
    assert entry is None


@pytest.mark.asyncio
async def test_convert_by_email_success(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="byemail@example.com")

    user_id = uuid.uuid4()
    entry = await WaitlistService.convert_by_email(
        db_session, email="byemail@example.com", user_id=user_id
    )

    assert entry is not None
    assert entry.status == WaitlistStatus.CONVERTED.value
    assert entry.converted_user_id == user_id


@pytest.mark.asyncio
async def test_convert_by_email_normalizes_lookup(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="normemail@example.com")

    user_id = uuid.uuid4()
    entry = await WaitlistService.convert_by_email(
        db_session, email="  NORMEMAIL@Example.COM ", user_id=user_id
    )

    assert entry is not None
    assert entry.converted_user_id == user_id


@pytest.mark.asyncio
async def test_convert_by_email_idempotent_when_already_converted(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="twice@example.com")

    first_user = uuid.uuid4()
    first = await WaitlistService.convert_by_email(
        db_session, email="twice@example.com", user_id=first_user
    )
    assert first is not None

    second_user = uuid.uuid4()
    second = await WaitlistService.convert_by_email(
        db_session, email="twice@example.com", user_id=second_user
    )

    assert second is not None
    assert second.status == WaitlistStatus.CONVERTED.value
    assert second.converted_user_id == first_user


# ─── get_stats ───────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_stats_empty_database(
    db_session: AsyncSession,
) -> None:
    stats = await WaitlistService.get_stats(db_session)
    assert stats == {
        "total": 0,
        "pending": 0,
        "invited": 0,
        "converted": 0,
        "expired": 0,
    }


@pytest.mark.asyncio
async def test_get_stats_counts_pending_entries(
    db_session: AsyncSession,
) -> None:
    for i in range(3):
        await WaitlistService.join_waitlist(
            db_session, email=f"pending{i}@example.com"
        )

    stats = await WaitlistService.get_stats(db_session)
    assert stats["total"] == 3
    assert stats["pending"] == 3
    assert stats["invited"] == 0
    assert stats["converted"] == 0


@pytest.mark.asyncio
async def test_get_stats_counts_mixed_statuses(
    db_session: AsyncSession,
) -> None:
    for i in range(4):
        await WaitlistService.join_waitlist(
            db_session, email=f"mix{i}@example.com"
        )

    # Invite 2 of them
    invited = await WaitlistService.invite_batch(db_session, count=2)
    # Convert 1 of those
    token = invited[0].invite_token
    assert token is not None
    await WaitlistService.convert_by_token(
        db_session, invite_token=token, user_id=uuid.uuid4()
    )

    # Mark one entry as expired manually
    entry = await WaitlistService.get_position(
        db_session, email="mix3@example.com"
    )
    assert entry is not None
    entry.status = WaitlistStatus.EXPIRED.value
    await db_session.flush()

    stats = await WaitlistService.get_stats(db_session)
    assert stats["total"] == 4
    assert stats["pending"] == 1
    assert stats["invited"] == 1
    assert stats["converted"] == 1
    assert stats["expired"] == 1


# ─── list_entries ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_entries_returns_empty_list_by_default(
    db_session: AsyncSession,
) -> None:
    entries = await WaitlistService.list_entries(db_session)
    assert entries == []


@pytest.mark.asyncio
async def test_list_entries_returns_all_without_filter(
    db_session: AsyncSession,
) -> None:
    for i in range(3):
        await WaitlistService.join_waitlist(
            db_session, email=f"listall{i}@example.com"
        )

    entries = await WaitlistService.list_entries(db_session)
    assert len(entries) == 3
    # FIFO order
    assert entries[0].position == 1
    assert entries[2].position == 3


@pytest.mark.asyncio
async def test_list_entries_filters_by_status(
    db_session: AsyncSession,
) -> None:
    for i in range(3):
        await WaitlistService.join_waitlist(
            db_session, email=f"filt{i}@example.com"
        )
    await WaitlistService.invite_batch(db_session, count=2)

    pending = await WaitlistService.list_entries(
        db_session, status_filter=WaitlistStatus.PENDING.value
    )
    invited = await WaitlistService.list_entries(
        db_session, status_filter=WaitlistStatus.INVITED.value
    )

    assert len(pending) == 1
    assert pending[0].status == WaitlistStatus.PENDING.value
    assert len(invited) == 2
    assert all(e.status == WaitlistStatus.INVITED.value for e in invited)


@pytest.mark.asyncio
async def test_list_entries_paginates_results(
    db_session: AsyncSession,
) -> None:
    for i in range(5):
        await WaitlistService.join_waitlist(
            db_session, email=f"page{i}@example.com"
        )

    page_one = await WaitlistService.list_entries(
        db_session, page=1, per_page=2
    )
    page_two = await WaitlistService.list_entries(
        db_session, page=2, per_page=2
    )
    page_three = await WaitlistService.list_entries(
        db_session, page=3, per_page=2
    )

    assert len(page_one) == 2
    assert len(page_two) == 2
    assert len(page_three) == 1

    assert page_one[0].position == 1
    assert page_two[0].position == 3
    assert page_three[0].position == 5


@pytest.mark.asyncio
async def test_list_entries_pagination_beyond_last_page(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="only@example.com")

    entries = await WaitlistService.list_entries(
        db_session, page=10, per_page=20
    )
    assert entries == []


@pytest.mark.asyncio
async def test_list_entries_status_filter_no_matches(
    db_session: AsyncSession,
) -> None:
    await WaitlistService.join_waitlist(db_session, email="nomatch@example.com")

    entries = await WaitlistService.list_entries(
        db_session, status_filter=WaitlistStatus.EXPIRED.value
    )
    assert entries == []
