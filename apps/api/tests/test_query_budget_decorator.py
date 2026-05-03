"""Tests for the @route_query_budget decorator (T2 / Sprint 55, ADR-0007).

The decorator stamps a `__query_budget__` attribute on the wrapped
endpoint so the QueryBudgetMiddleware (and the conftest test fixture)
can read the declared budget without inspecting the original signature.

Pure decorator behaviour — no I/O, no async runtime, no DB coupling.
These tests intentionally pre-date the implementation; they are the
contract `query_budget.py` must satisfy.
"""

from __future__ import annotations

import pytest

from app.core.query_budget import (
    NoQueryBudgetDeclaredError,
    get_route_query_budget,
    route_query_budget,
)


class TestRouteQueryBudgetDecorator:
    """`@route_query_budget(max_queries=N)` stamps and is introspectable."""

    def test_decorator_stamps_max_queries_on_endpoint(self) -> None:
        @route_query_budget(max_queries=4)
        async def endpoint() -> dict[str, str]:
            return {"ok": "1"}

        assert endpoint.__query_budget__ == 4

    def test_decorator_preserves_callable_identity(self) -> None:
        async def original() -> int:
            return 42

        wrapped = route_query_budget(max_queries=3)(original)

        # The decorator must NOT replace the function object — middleware
        # introspects the original handler, and FastAPI relies on the
        # identity for dependency-injection resolution.
        assert wrapped is original

    def test_decorator_preserves_name_and_qualname(self) -> None:
        @route_query_budget(max_queries=1)
        async def get_dashboard() -> None:
            return None

        assert get_dashboard.__name__ == "get_dashboard"

    def test_decorator_rejects_zero_or_negative(self) -> None:
        with pytest.raises(ValueError, match="max_queries must be >= 1"):

            @route_query_budget(max_queries=0)
            async def bad() -> None:
                return None

        with pytest.raises(ValueError, match="max_queries must be >= 1"):

            @route_query_budget(max_queries=-1)
            async def worse() -> None:
                return None

    def test_decorator_rejects_unreasonable_ceiling(self) -> None:
        # A budget of 1000 is almost certainly a bug — it's an annotation
        # that disables the gate entirely. Force the author to flag the
        # bypass via the `no_query_budget` pytest marker instead.
        with pytest.raises(ValueError, match="max_queries must be <= 100"):

            @route_query_budget(max_queries=10_000)
            async def runaway() -> None:
                return None


class TestGetRouteQueryBudget:
    """`get_route_query_budget(endpoint)` returns the stamped budget or
    raises so the middleware can distinguish 'not annotated yet' from
    'annotated as zero-query'."""

    def test_returns_stamped_value(self) -> None:
        @route_query_budget(max_queries=7)
        async def annotated() -> None:
            return None

        assert get_route_query_budget(annotated) == 7

    def test_raises_when_not_annotated(self) -> None:
        async def bare() -> None:
            return None

        with pytest.raises(NoQueryBudgetDeclaredError):
            get_route_query_budget(bare)

    def test_raises_for_non_callable(self) -> None:
        with pytest.raises(NoQueryBudgetDeclaredError):
            get_route_query_budget("not a callable")  # type: ignore[arg-type]
