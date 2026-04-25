"""
PathForge API — Query Budget Decorator (T2 / Sprint 55, ADR-0007)
==================================================================

Each route handler declares an upper bound on the number of database
queries it should execute per request.  The declared budget is stamped
onto the endpoint via this decorator and is later read by:

* :class:`app.core.middleware.QueryBudgetMiddleware` — emits
  ``x-query-count`` (non-prod) or a Sentry breadcrumb (prod) when the
  count exceeds the budget.
* The pytest autouse fixture in ``tests/conftest.py`` — fails the test
  suite when any request executes more queries than its declared budget.

This module is intentionally **pure**: no I/O, no async runtime, no DB
coupling.  The decorator is identity-preserving so FastAPI's
dependency-injection machinery sees the original handler.

Usage
-----

.. code-block:: python

    from app.core.query_budget import route_query_budget

    @router.get("/career-dna/dashboard")
    @route_query_budget(max_queries=4)
    async def get_dashboard(...): ...

Bypass
------

For routes that intentionally sidestep the budget (raw integration
probes, admin tooling), do **not** use a sky-high ``max_queries`` —
mark the test instead with ``@pytest.mark.no_query_budget``.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from typing import Any, TypeVar

# Lower bound: `route_query_budget(max_queries=0)` is almost certainly a
# typo. A budget of zero queries means the endpoint cannot touch the DB
# at all — there is no legitimate use case for declaring it explicitly
# (such handlers don't depend on `get_db`, so the middleware short-
# circuits anyway).
_MIN_BUDGET = 1

# Upper bound: `route_query_budget(max_queries=10_000)` disables the
# gate. We force the bypass to be explicit (pytest marker) rather than
# silent (a number nobody will ever cross). 100 is generous — the
# largest legitimate budget on the current handler set is the
# multi-engine dashboard at ~12 queries.
_MAX_BUDGET = 100

#: Attribute name used to stamp the budget onto the endpoint. Public so
#: the middleware and conftest fixture can ``getattr`` against it
#: without re-importing the symbol.
QUERY_BUDGET_ATTR = "__query_budget__"

# Bound is `Callable[..., Any]` (not `Awaitable[...]`) so synchronous
# FastAPI handlers — fully supported by the framework — can also be
# annotated. The decorator is identity-preserving regardless of
# coroutine-ness.
_F = TypeVar("_F", bound=Callable[..., Any])


class NoQueryBudgetDeclaredError(LookupError):
    """Raised when an endpoint is asked for its budget but never had one
    stamped. The middleware treats this as a soft-fail in production
    (logs a warning, lets the request through) and the conftest fixture
    treats it as a hard fail (every prod handler MUST be annotated).
    """


def route_query_budget(*, max_queries: int) -> Callable[[_F], _F]:
    """Stamp ``max_queries`` onto the wrapped endpoint.

    Parameters
    ----------
    max_queries:
        Upper bound on DB queries per request, inclusive. Must be in
        ``[1, 100]``. The bound forces every legitimate budget to be
        considered: anything outside the range is either a typo or a
        signal that the handler should be split.

    Returns
    -------
    Callable
        The original endpoint, unchanged except for the
        ``__query_budget__`` attribute. **Identity is preserved** so
        FastAPI's DI resolution and ``request.scope["route"].endpoint``
        continue to point at the same callable.

    Raises
    ------
    ValueError
        If ``max_queries`` is outside ``[1, 100]``.
    """
    if max_queries < _MIN_BUDGET:
        raise ValueError(
            f"max_queries must be >= {_MIN_BUDGET} (got {max_queries}). "
            "A budget of zero would disable the gate without surfacing intent."
        )
    if max_queries > _MAX_BUDGET:
        raise ValueError(
            f"max_queries must be <= {_MAX_BUDGET} (got {max_queries}). "
            "If a higher budget is genuinely needed, split the handler — "
            "or mark the relevant test with @pytest.mark.no_query_budget."
        )

    def decorate(endpoint: _F) -> _F:
        setattr(endpoint, QUERY_BUDGET_ATTR, max_queries)
        return endpoint

    return decorate


def get_route_query_budget(endpoint: object) -> int:
    """Return the budget stamped by :func:`route_query_budget`.

    Raises :class:`NoQueryBudgetDeclaredError` when the endpoint is not
    a callable that carries the stamped attribute. Callers that prefer
    a sentinel can wrap the call in ``try/except``.
    """
    if not callable(endpoint):
        raise NoQueryBudgetDeclaredError(
            f"Cannot read query budget from non-callable: {endpoint!r}"
        )
    # `inspect.unwrap` peels off intermediate decorators (e.g.
    # `@limiter.limit`, `@functools.wraps`-style wrappers) so the
    # budget annotation is found on the underlying handler regardless
    # of decoration order. The unwrap walks `__wrapped__` chains and
    # stops at the first object without one, so a bare endpoint is
    # returned unchanged.
    target = inspect.unwrap(endpoint)
    budget = getattr(target, QUERY_BUDGET_ATTR, None)
    if budget is None:
        # Fall back to the original object: callers that intentionally
        # stamp on the wrapper (rare, but the API allows it) still get
        # picked up.
        budget = getattr(endpoint, QUERY_BUDGET_ATTR, None)
    if budget is None:
        qualname = getattr(endpoint, "__qualname__", repr(endpoint))
        raise NoQueryBudgetDeclaredError(
            f"{qualname} has no @route_query_budget annotation"
        )
    return int(budget)
