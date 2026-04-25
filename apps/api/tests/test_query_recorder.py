"""Tests for the QueryRecorder (T2 / Sprint 55, ADR-0007).

Counts SQL statements that flow through the application's async engine
on a per-request basis using a ``ContextVar``.  Engine-name (the
"principal" of the request, e.g. ``career_dna``) is derived from the
URL path so the future Causality Ledger can attribute outcomes back to
the engine chain that touched the user.

These tests pre-date the implementation; they pin the contract.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest

from app.core.query_recorder import (
    DEFAULT_ENGINE_NAME,
    QueryCounter,
    derive_engine_name,
    query_counter_var,
    register_query_counter_listener,
)


class TestEngineNameDerivation:
    """Engine name = first non-version path segment.

    The Causality Ledger (ADR-0007) needs a stable, low-cardinality
    label per outcome event, so we use the route prefix rather than the
    full path. ``/api/v1/career-dna/dashboard`` → ``career_dna``.
    Hyphens normalise to underscores so the label round-trips through
    Sentry tags + Langfuse traces without quoting.
    """

    @pytest.mark.parametrize(
        ("path", "expected"),
        [
            ("/api/v1/career-dna/dashboard", "career_dna"),
            ("/api/v1/threat-radar/scan", "threat_radar"),
            ("/api/v1/auth/login", "auth"),
            ("/api/v1/users/me", "users"),
            ("/api/v1/", DEFAULT_ENGINE_NAME),
            ("/api/v1", DEFAULT_ENGINE_NAME),
            # Non-API top-level prefixes keep their first segment so
            # health-probe queries can be grouped separately from user
            # traffic in the Causality Ledger.
            ("/health/ready", "health"),
            ("/health", "health"),
            ("/", DEFAULT_ENGINE_NAME),
            ("", DEFAULT_ENGINE_NAME),
        ],
    )
    def test_derive_engine_name(self, path: str, expected: str) -> None:
        assert derive_engine_name(path) == expected


class TestQueryCounter:
    """The per-request counter has minimal moving parts and a single
    side-effect path: ``increment()`` is called by the SQLAlchemy event
    listener registered via :func:`register_query_counter_listener`.
    """

    def test_initial_state(self) -> None:
        counter = QueryCounter(engine_name="career_dna")
        assert counter.count == 0
        assert counter.engine_name == "career_dna"

    def test_increment_increases_count(self) -> None:
        counter = QueryCounter(engine_name="auth")
        counter.increment()
        counter.increment()
        counter.increment()
        assert counter.count == 3

    def test_counter_var_default_is_none(self) -> None:
        # When no request scope has installed a counter (e.g. background
        # ARQ tasks), the contextvar must report ``None`` so callers
        # know to skip recording instead of silently mutating a
        # dangling counter.
        assert query_counter_var.get() is None


@pytest.fixture
async def isolated_engine() -> AsyncGenerator[Any, None]:
    """A fresh in-memory async engine for listener-mechanics tests.

    The conftest ``db_session`` fixture wraps every test in nested
    SAVEPOINT machinery that emits its own bookkeeping statements —
    fine for transactional isolation, but it makes "exact count"
    assertions brittle.  This fixture gives the listener tests a clean
    surface where every cursor execution is a user-issued query.
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    try:
        yield eng
    finally:
        await eng.dispose()


@pytest.mark.asyncio
class TestSqlAlchemyEventListener:
    """Wiring test: registering the listener increments the active
    counter once per cursor execution.

    Uses an isolated in-memory async engine to keep bookkeeping noise
    from the project's transactional fixture out of the assertions.
    """

    async def test_listener_counts_executed_statements(
        self, isolated_engine: Any
    ) -> None:
        """Each user-issued ``execute`` increments the counter exactly
        once.  Counts via delta so the test is insensitive to bookkeeping
        statements emitted by the test fixture's SAVEPOINT pattern.
        """
        from sqlalchemy import text

        register_query_counter_listener()
        counter = QueryCounter(engine_name="test_engine")
        token = query_counter_var.set(counter)
        try:
            async with isolated_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                await conn.execute(text("SELECT 2"))
        finally:
            query_counter_var.reset(token)

        assert counter.count == 2

    async def test_listener_is_idempotent_when_called_twice(
        self, isolated_engine: Any
    ) -> None:
        """Registering the listener twice must not double-count — the
        helper guards against re-registration on test-suite re-import.
        """
        from sqlalchemy import text

        register_query_counter_listener()
        register_query_counter_listener()  # second call: no-op

        counter = QueryCounter(engine_name="test_engine")
        token = query_counter_var.set(counter)
        try:
            async with isolated_engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
        finally:
            query_counter_var.reset(token)

        # Exactly one increment; double-registration would double-count.
        assert counter.count == 1

    async def test_listener_is_silent_when_no_counter_installed(
        self, isolated_engine: Any
    ) -> None:
        """Background jobs / startup probes execute SQL without an
        active request scope. The listener must short-circuit instead
        of raising.
        """
        from sqlalchemy import text

        register_query_counter_listener()
        # No `query_counter_var.set(...)` — counter is None.
        async with isolated_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))  # must not raise
