"""
PathForge — Sprint 61 TransparencyLog SQLite round-trip tests
==============================================================

Closes the last ~50 lines of uncovered code in
``app/core/llm_observability.py`` — the **happy paths** of the four
DB methods that fall back to Postgres when the in-memory buffer
misses:

  - ``_persist_to_db``
  - ``_load_recent_from_db``
  - ``_load_by_id_from_db``
  - ``_load_user_for_analysis_from_db``

Sprint 60 covered failure paths via mocked sessions. The remaining
gap was the success path — which previously required a real
Postgres because production code went straight to
``app.core.database.async_session_factory``.

Sprint 61 added a constructor-injectable ``session_factory`` to
``TransparencyLog`` so we can wire the same ORM path against the
hermetic SQLite engine the rest of the suite uses. These tests
exercise:

  - Round-trip persist + load-by-id (write returns the same record).
  - Round-trip persist + load-recent honours per-user filtering and
    ``order_by(created_at desc)`` + ``LIMIT``.
  - ``get_user_for_analysis`` round-trip returns the owning user's
    UUID string.
  - ``get_by_id`` falls through to DB when the in-memory buffer was
    cleared (process restart simulation).
  - ``get_user_for_analysis`` returns ``None`` for an unknown id.

The fixtures lean on the existing ``test_engine`` (session-scoped
SQLite-in-memory with all tables created) but build a *fresh*
``async_sessionmaker`` per test so the round-trip transaction is
not entangled with the outer ``db_session`` savepoint envelope.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.llm_observability import TransparencyLog, TransparencyRecord

pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def sqlite_session_factory(
    test_engine: Any,
) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    """A fresh ``async_sessionmaker`` bound to the session-scoped
    test engine. Each test gets a clean ``ai_transparency_records``
    table so the assertions are deterministic.
    """
    from app.models.ai_transparency import AITransparencyRecord

    factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False,
    )

    # Truncate the table so prior tests' rows don't leak.
    async with factory() as session:
        await session.execute(AITransparencyRecord.__table__.delete())
        await session.commit()

    yield factory

    async with factory() as session:
        await session.execute(AITransparencyRecord.__table__.delete())
        await session.commit()


def _make_record(
    *,
    analysis_id: str | None = None,
    analysis_type: str = "career_dna",
    confidence_score: float = 0.83,
    success: bool = True,
    latency_ms: int = 250,
) -> TransparencyRecord:
    return TransparencyRecord(
        analysis_id=analysis_id or str(uuid.uuid4()),
        analysis_type=analysis_type,
        model="claude-sonnet-4",
        tier="primary",
        confidence_score=confidence_score,
        confidence_label="High",
        data_sources=["resume", "skills_taxonomy"],
        prompt_tokens=120,
        completion_tokens=240,
        latency_ms=latency_ms,
        success=success,
        retries=0,
    )


# ─────────────────────────────────────────────────────────────────
# 1. Persist round-trip
# ─────────────────────────────────────────────────────────────────


class TestPersistAndLoadById:
    """Write via ``_persist_to_db`` then read via ``_load_by_id_from_db``."""

    async def test_persisted_record_loads_back_with_full_field_set(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        user_id = str(uuid.uuid4())
        analysis_id = str(uuid.uuid4())
        rec = _make_record(analysis_id=analysis_id)

        await log._persist_to_db(user_id=user_id, entry=rec)

        loaded = await log._load_by_id_from_db(analysis_id)
        assert loaded is not None
        assert loaded.analysis_id == analysis_id
        assert loaded.analysis_type == "career_dna"
        assert loaded.model == "claude-sonnet-4"
        assert loaded.tier == "primary"
        assert loaded.confidence_score == pytest.approx(0.83)
        assert loaded.confidence_label == "High"
        assert loaded.data_sources == ["resume", "skills_taxonomy"]
        assert loaded.prompt_tokens == 120
        assert loaded.completion_tokens == 240
        assert loaded.latency_ms == 250
        assert loaded.success is True
        assert loaded.retries == 0
        # ``created_at`` is server-set so we just check it's a non-empty
        # ISO-shaped string.
        assert "T" in loaded.timestamp

    async def test_load_by_id_returns_none_for_unknown_after_persist(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        await log._persist_to_db(
            user_id=str(uuid.uuid4()),
            entry=_make_record(),
        )
        assert (
            await log._load_by_id_from_db(str(uuid.uuid4()))
        ) is None


# ─────────────────────────────────────────────────────────────────
# 2. Load-recent round-trip — per-user filtering + ordering
# ─────────────────────────────────────────────────────────────────


class TestLoadRecentRoundTrip:
    async def test_load_recent_returns_user_rows_only_newest_first(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        user_a = str(uuid.uuid4())
        user_b = str(uuid.uuid4())

        # Persist 3 for user_a and 2 for user_b. Sleep micro-pauses
        # are required to give the SQLite ``created_at`` server
        # default (CURRENT_TIMESTAMP, second-resolution) distinct
        # values so the ORDER BY is deterministic.
        for i in range(3):
            await log._persist_to_db(
                user_id=user_a,
                entry=_make_record(analysis_type=f"type_a_{i}"),
            )
            await asyncio.sleep(1.05)
        for i in range(2):
            await log._persist_to_db(
                user_id=user_b,
                entry=_make_record(analysis_type=f"type_b_{i}"),
            )
            await asyncio.sleep(1.05)

        # User A — newest first, filtered to A only.
        a_recs = await log._load_recent_from_db(user_id=user_a, limit=10)
        assert len(a_recs) == 3
        assert all(r.analysis_type.startswith("type_a") for r in a_recs)
        # The newest (i=2) comes first.
        assert a_recs[0].analysis_type == "type_a_2"
        assert a_recs[-1].analysis_type == "type_a_0"

        # User B — only 2 rows.
        b_recs = await log._load_recent_from_db(user_id=user_b, limit=10)
        assert len(b_recs) == 2

    async def test_load_recent_honours_limit(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        user_id = str(uuid.uuid4())
        for i in range(5):
            await log._persist_to_db(
                user_id=user_id,
                entry=_make_record(analysis_type=f"a{i}"),
            )
            await asyncio.sleep(1.05)
        recs = await log._load_recent_from_db(user_id=user_id, limit=3)
        assert len(recs) == 3

    async def test_load_recent_returns_empty_for_unknown_user(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        recs = await log._load_recent_from_db(
            user_id=str(uuid.uuid4()), limit=10,
        )
        assert recs == []


# ─────────────────────────────────────────────────────────────────
# 3. user_for_analysis round-trip
# ─────────────────────────────────────────────────────────────────


class TestLoadUserForAnalysisRoundTrip:
    async def test_returns_user_id_for_persisted_analysis(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        user_id = str(uuid.uuid4())
        analysis_id = str(uuid.uuid4())
        await log._persist_to_db(
            user_id=user_id,
            entry=_make_record(analysis_id=analysis_id),
        )
        out = await log._load_user_for_analysis_from_db(analysis_id)
        assert out == user_id

    async def test_returns_none_for_unknown_analysis(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        out = await log._load_user_for_analysis_from_db(str(uuid.uuid4()))
        assert out is None


# ─────────────────────────────────────────────────────────────────
# 4. Public API falls through to DB on in-memory miss
# ─────────────────────────────────────────────────────────────────


class TestPublicApiFallthrough:
    """``get_recent`` / ``get_by_id`` / ``get_user_for_analysis``
    should hit the DB when the in-memory buffer is empty (post-
    process-restart). We persist directly via the DB method, then
    call the public method and assert it returned the persisted row
    even though ``log._records`` is empty."""

    async def test_get_by_id_falls_through_to_db_after_buffer_cleared(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        analysis_id = str(uuid.uuid4())
        await log._persist_to_db(
            user_id=str(uuid.uuid4()),
            entry=_make_record(analysis_id=analysis_id),
        )

        # In-memory buffer is empty (we never called ``record``);
        # ``get_by_id`` must fall through to ``_load_by_id_from_db``.
        loaded = await log.get_by_id(analysis_id)
        assert loaded is not None
        assert loaded.analysis_id == analysis_id

    async def test_get_user_for_analysis_falls_through_to_db(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        user_id = str(uuid.uuid4())
        analysis_id = str(uuid.uuid4())
        await log._persist_to_db(
            user_id=user_id,
            entry=_make_record(analysis_id=analysis_id),
        )
        out = await log.get_user_for_analysis(analysis_id)
        assert out == user_id

    async def test_get_recent_falls_through_to_db(
        self,
        sqlite_session_factory: async_sessionmaker[AsyncSession],
    ) -> None:
        log = TransparencyLog(session_factory=sqlite_session_factory)
        user_id = str(uuid.uuid4())
        await log._persist_to_db(
            user_id=user_id,
            entry=_make_record(),
        )
        recs = await log.get_recent(user_id, limit=5)
        # ``get_recent`` returned from DB because ``_records`` is empty.
        assert len(recs) == 1


# ─────────────────────────────────────────────────────────────────
# 5. Default-factory contract preserved
# ─────────────────────────────────────────────────────────────────


class TestDefaultFactoryContract:
    """When ``session_factory`` is not passed, ``_get_session_factory``
    must return the production ``async_session_factory`` import. We
    don't open a session here — Postgres is not reachable — we only
    assert the identity of the returned object."""

    async def test_default_factory_is_production_singleton(self) -> None:
        from app.core.database import async_session_factory

        log = TransparencyLog()
        assert log._get_session_factory() is async_session_factory

    async def test_injected_factory_overrides_default(self) -> None:
        sentinel: Any = object()
        log = TransparencyLog(session_factory=sentinel)
        assert log._get_session_factory() is sentinel
