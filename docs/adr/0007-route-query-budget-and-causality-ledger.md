# ADR-0007 — Per-Route Query Budget & Engine-of-Record Causality Ledger

* **Status:** Accepted
* **Sprint:** 55 (T2 of `docs/architecture/sprint-55-58-code-side-readiness.md`)
* **Closes:** P2-4 (`docs/MASTER_PRODUCTION_READINESS.md` §4 Gate B)
* **Date:** 2026-04-25
* **Author:** PathForge engineering
* **Reviewers:** belengaz, reso, pizmam

## Context

`warn_on_lazy_load` (Sprint 44) catches accidental lazy-loads at test
time, but as `UserWarning` only. We had:

* **No per-endpoint budget.** Every route silently agreed to "as many
  queries as it takes," which is how N+1 regressions slip in without a
  CI failure.
* **No production observability.** Nothing told us when a route in
  prod ran 12 queries on a request the developer thought was 3.
* **No regression gate in CI.** A new feature could land doubling the
  query count of a hot endpoint and only show up post-deploy in a
  Sentry latency tail.

PathForge also lacks a primitive that competitors with monolithic AI
layers cannot easily produce: a per-user **causality ledger** that
attributes outcome events ("offer accepted", "role transitioned") to
the engine chain that touched the user in the preceding window. This
is the central enterprise-sales differentiator framed in
`docs/architecture/sprint-55-58-code-side-readiness.md` §1.3 / §3.4.

The two needs share a primitive: a per-request, engine-keyed counter
of database activity. This ADR records the decision to land both as
one cohesive piece of infrastructure rather than two parallel ones.

## Decision

Each route handler **declares** its query budget via decorator. A
middleware **records** the actual count. A test-suite autouse fixture
**enforces** the declaration. Engine name (the route's principal
engine — `career_dna`, `threat_radar`, …) is captured at request-start
and forms the keying tuple for the future Causality Ledger.

```python
# Declaration — stamps `__query_budget__` onto the endpoint
@router.get("/career-dna/dashboard")
@route_query_budget(max_queries=4)
async def get_dashboard(...): ...

# Recording — SQLAlchemy after_cursor_execute event listener
# scoped via ContextVar to the active request
QueryCounter(engine_name="career_dna")  # set by middleware

# Enforcement — autouse pytest fixture asserts observed ≤ declared
# per request, captures observations into a registry, fails the test
# on overage. Bypass with @pytest.mark.no_query_budget.
```

## Considered alternatives

* **Monitor without declaration.** Rejected — produces a dashboard
  nobody actions. Without a target, we never know "is 8 queries on
  this route a problem?"
* **Auto-derive budgets from current production p95.** Rejected —
  locks in the current bugs; a regressed endpoint becomes its own
  baseline. Each annotation is an explicit owner statement.
* **`sqlalchemy.event.listen("after_cursor_execute")` only, no
  declaration.** Adopted as the **recording** mechanism, but not as
  the **declaration** mechanism. Both layers needed: recording without
  budgets is metrics theatre.
* **Route-prefix → engine map in a config file.** Rejected. Engine
  derivation from the URL path keeps the source of truth at the route
  declaration site. A config file would drift the day someone
  re-mounts a router.

## Implementation

| Layer | Module | Responsibility |
|:---|:---|:---|
| Declaration | `app.core.query_budget` | `@route_query_budget(max_queries=N)` stamps `__query_budget__`. Identity-preserving. |
| Recording | `app.core.query_recorder` | `QueryCounter` + ContextVar + SQLAlchemy `after_cursor_execute` listener. |
| Enforcement (prod) | `app.core.middleware.QueryBudgetMiddleware` | `x-query-count` header in non-prod; Sentry breadcrumb on overage in prod. |
| Enforcement (tests) | `tests/conftest.py::_enforce_route_query_budgets` | Autouse fixture; hard-fails the test on overage. |
| Reporting | `tests/test_query_budgets.py` | Renders the registry into a sortable Markdown table for CI artefact upload. |
| Bypass | `pyproject.toml [tool.pytest.ini_options].markers` | `no_query_budget` marker for raw integration probes. |

### Listener placement

The listener is registered on the `sqlalchemy.engine.Engine` *class*
rather than a specific engine instance. That way the production async
engine, the conftest in-memory sqlite engine, and any future
per-tenant engine all emit through the same handler. The handler
short-circuits when no `QueryCounter` is installed in the current
context, so non-request DB I/O (background ARQ jobs, Alembic
migrations) is uncounted by design.

### Causality keying

`QueryCounter(engine_name=…)` is keyed at request start by deriving
the engine name from the URL path (`/api/v1/career-dna/dashboard` →
`career_dna`). Engine name is treated as immutable for the request
lifetime — re-keying would corrupt downstream invariants when the
ledger lands in T4 (Langfuse traces) and the analytics layer.

## Differentiation hook

With the engine-keyed counter live, a future analytics flow can
associate any user-success event in `app.services.analytics_service`
with the engine chain that touched the user in the preceding 24-hour
window. The query-count contextvar effectively becomes the
"intermediary" the Causality Ledger attaches to. No competitor with a
monolithic AI layer can produce this attribution; ours is naturally
falling out of the per-engine accounting.

## Privacy & GDPR

The Causality Ledger is per-user. Default retention is **90 days
rolling** (sprint-plan §12 default decision #3). Aggregates are
anonymised before retention longer than 90 days. The existing
`DELETE /api/v1/users/me` endpoint cascades through the ledger via
the `user_id` foreign key (T2 follow-up adds the table; this ADR
records the design). PII redaction is unchanged from the Langfuse
pipeline — engine names + counts only, no payloads.

## Rollback

Rollback is feature-flag-free: a single PR removing the
`add_middleware(QueryBudgetMiddleware)` line in `apps/api/app/main.py`
restores the prior behaviour. The decorator and listener can stay in
place without observable impact (decorator is a no-op without the
middleware reading it; listener short-circuits without a counter).

## Performance impact

* Per-request overhead is **one ContextVar set + one ContextVar reset
  + one dict lookup** (engine name derivation is `str.split` on the
  path). Bench target: ≤ 1 ms p99 added on `/health/ready`.
* SQLAlchemy event listener adds **one Python function call per
  cursor execute** plus a ContextVar.get + None check. On a request
  running 4 queries, this is ≈ 12 µs aggregate overhead.

A `hyperfine` benchmark run pre/post-T2 is captured in the T2 PR
description (target: ≤ 1 ms p99 delta).

## Quality gate

Per `docs/architecture/sprint-55-58-code-side-readiness.md` §3.5 (T2):

| Criterion | Target | Verification |
|:---|:---:|:---|
| Route handlers annotated | 100 % (after rollout PR) | grep + lint rule |
| 95th-percentile budget violations | 0 | CI artefact (`query-budget-report.md`) |
| New tests | ≥ 15 | 31 landed in this ADR's PR (decorator 8, recorder 16, middleware 7) |
| Production overhead | ≤ 1 ms p99 | hyperfine bench on `/health/ready` |

## References

* `docs/architecture/sprint-55-58-code-side-readiness.md` §3 (T2)
* `docs/MASTER_PRODUCTION_READINESS.md` §4 Gate B (P2-4)
* SQLAlchemy event API — `after_cursor_execute`
* Stripe Engineering — *"Workflow patterns for production reliability"*
  (the budget-as-declaration pattern parallels Stripe's per-endpoint
  rate-limit declarations)

## Status notes

The infrastructure (decorator, recorder, middleware, conftest fixture,
report) lands in **PR T2-infra**. Annotation rollout across all ~60
route handlers — measuring observed p95 from the test suite, applying
each annotation with 20% headroom — lands in **PR T2-rollout**. The
two-PR split keeps each diff reviewable and lets the
infrastructure bake on `dev` before ~60 file touches go in.
