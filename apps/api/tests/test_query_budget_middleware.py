"""Tests for the QueryBudgetMiddleware (T2 / Sprint 55, ADR-0007).

The middleware:

1. Allocates a fresh :class:`QueryCounter` per request, keyed on the
   engine name derived from the URL path.
2. Lets the route handler run.
3. After the response is built, reads the route's declared budget via
   :func:`app.core.query_budget.get_route_query_budget`.
4. In **non-production** environments adds an ``x-query-count`` header
   so developers see budget consumption in HTTP traces.
5. On **budget excess** in production emits a Sentry breadcrumb with
   the engine + endpoint name + actual count + budget — the SRE
   surface the Engine-of-Record Causality Ledger feeds off.

These tests exercise the middleware against a stub FastAPI app so they
don't depend on the production router wiring.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.core.middleware import QueryBudgetMiddleware
from app.core.query_budget import route_query_budget
from app.core.query_recorder import (
    register_query_counter_listener,
)

# This module exercises overage paths intentionally — opt the whole
# file out of the autouse enforcement fixture in conftest.
pytestmark = pytest.mark.no_query_budget


@pytest.fixture(scope="module", autouse=True)
def _ensure_listener_registered() -> None:
    """The middleware relies on the SQLAlchemy listener being live; in
    production the FastAPI lifespan registers it once.  Ensure it's
    registered before any test in this module runs.
    """
    register_query_counter_listener()


@pytest.fixture
def isolated_async_engine() -> Any:
    return create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)


@pytest.fixture
def app_with_middleware(
    isolated_async_engine: Any,
) -> FastAPI:
    """Build a stub app that mounts the middleware and exposes a
    handler whose query count is controllable from each test."""
    app = FastAPI()

    async def _exec(n_queries: int) -> None:
        async with isolated_async_engine.connect() as conn:
            for _ in range(n_queries):
                await conn.execute(text("SELECT 1"))

    @app.get("/api/v1/career-dna/dashboard")
    @route_query_budget(max_queries=2)
    async def under_budget() -> dict[str, str]:
        await _exec(2)
        return {"ok": "1"}

    @app.get("/api/v1/threat-radar/scan")
    @route_query_budget(max_queries=2)
    async def over_budget() -> dict[str, str]:
        await _exec(5)
        return {"ok": "1"}

    @app.get("/api/v1/legacy/no-annotation")
    async def no_budget() -> dict[str, str]:
        await _exec(1)
        return {"ok": "1"}

    app.add_middleware(QueryBudgetMiddleware)
    return app


class TestNonProductionHeader:
    """In non-prod, every response carries ``x-query-count`` so the
    developer sees the cost of the request without a tail-tap.
    """

    def test_header_reports_actual_count_under_budget(self, app_with_middleware: FastAPI) -> None:
        with patch("app.core.middleware.settings.environment", "development"):
            client = TestClient(app_with_middleware)
            resp = client.get("/api/v1/career-dna/dashboard")

        assert resp.status_code == 200
        assert resp.headers["x-query-count"] == "2"
        # Engine name is also exposed for ad-hoc telemetry parsing.
        assert resp.headers["x-query-engine"] == "career_dna"

    def test_header_reports_overage_in_non_prod(self, app_with_middleware: FastAPI) -> None:
        with patch("app.core.middleware.settings.environment", "development"):
            client = TestClient(app_with_middleware)
            resp = client.get("/api/v1/threat-radar/scan")

        # The middleware MUST NOT block the response on overage in
        # non-prod — developers want to see the violation, not 500s.
        assert resp.status_code == 200
        assert resp.headers["x-query-count"] == "5"

    def test_header_omitted_for_unannotated_route(self, app_with_middleware: FastAPI) -> None:
        """Without an annotation we can't compare to a budget, but the
        actual count is still useful for inventory work.  Header is
        present; no overage warning.
        """
        with patch("app.core.middleware.settings.environment", "development"):
            client = TestClient(app_with_middleware)
            resp = client.get("/api/v1/legacy/no-annotation")

        assert resp.status_code == 200
        assert resp.headers["x-query-count"] == "1"


class TestProductionBreadcrumb:
    """In prod, the header is suppressed and overages emit a structured
    Sentry breadcrumb so the SRE surface (and the future Causality
    Ledger) can consume the signal.  Logging contracts are stable;
    direct Sentry SDK calls are mocked in unit scope.
    """

    def test_no_header_in_production(self, app_with_middleware: FastAPI) -> None:
        with patch("app.core.middleware.settings.environment", "production"):
            client = TestClient(app_with_middleware)
            resp = client.get("/api/v1/career-dna/dashboard")

        assert resp.status_code == 200
        assert "x-query-count" not in resp.headers
        assert "x-query-engine" not in resp.headers

    def test_overage_emits_breadcrumb_in_production(self, app_with_middleware: FastAPI) -> None:
        with (
            patch("app.core.middleware.settings.environment", "production"),
            patch("app.core.middleware._emit_budget_overage_breadcrumb") as mock_bc,
        ):
            client = TestClient(app_with_middleware)
            resp = client.get("/api/v1/threat-radar/scan")

        assert resp.status_code == 200
        mock_bc.assert_called_once()
        kwargs = mock_bc.call_args.kwargs
        assert kwargs["actual"] == 5
        assert kwargs["budget"] == 2
        assert kwargs["engine_name"] == "threat_radar"
        assert kwargs["path"] == "/api/v1/threat-radar/scan"

    def test_no_breadcrumb_when_under_budget(self, app_with_middleware: FastAPI) -> None:
        with (
            patch("app.core.middleware.settings.environment", "production"),
            patch("app.core.middleware._emit_budget_overage_breadcrumb") as mock_bc,
        ):
            client = TestClient(app_with_middleware)
            resp = client.get("/api/v1/career-dna/dashboard")

        assert resp.status_code == 200
        mock_bc.assert_not_called()


@pytest.mark.asyncio
async def test_middleware_does_not_corrupt_counter_var_after_request(
    app_with_middleware: FastAPI,
) -> None:
    """The middleware must reset the contextvar via ``token`` so a
    second request (or a background task started during one) sees a
    clean slate.  Direct check on the contextvar after a TestClient
    call.
    """
    from app.core.query_recorder import query_counter_var

    with patch("app.core.middleware.settings.environment", "development"):
        client = TestClient(app_with_middleware)
        client.get("/api/v1/career-dna/dashboard")

    assert query_counter_var.get() is None


# Reference (silence unused import warning when running this module
# stand-alone outside the rest of the suite).
_ = AsyncSession
