# ADR-0003: Circuit Breaker Adopted for External API Calls

- **Status**: Accepted
- **Date**: 2026-04-23
- **Deciders**: Senior Staff Engineer (PathForge quality-playbook authority)
- **Context links**: [ADR-0002](0002-redis-ssl-secure-by-default.md), MASTER_PRODUCTION_READINESS.md § P2-3, Sprint-43

## Context

PathForge makes external API calls to three services:

| Service | Call site | Failure impact |
|:--|:--|:--|
| **Adzuna** | `AdzunaProvider.search()` — `httpx.get` | Empty job search results |
| **Jooble** | `JoobleProvider.search()` — `httpx.post` | Empty job search results |
| **Voyage AI** | `EmbeddingService.embed_text/batch()` — `asyncio.to_thread` | Broken resume/job matching |

All three callers already implement graceful degradation (log + return empty or raise). The problem is throughput under sustained outage: every request still initiates a full HTTP round-trip before timing out (30 s default), consuming event-loop time and connection-pool slots for the duration of the outage. Under concurrent load this fans into many simultaneous blocked requests.

A production-ready `CircuitBreaker` class (`app/core/circuit_breaker.py`, Sprint-42) was built to solve this with Redis-backed shared state. It was never wired to any caller — tracked as P2-3 in MASTER_PRODUCTION_READINESS.md.

**Blocking dependency — OPS-4**: Redis is not yet provisioned in production. This ADR resolves the risk by adding `fail_open=True` (default) to the circuit breaker, so Redis becomes a soft dependency: circuit checks are skipped gracefully when Redis is unavailable rather than becoming a secondary failure vector.

## Decision

**Adopt** the existing `CircuitBreaker` by wiring it into all three external call sites and extending the class with a `fail_open` parameter.

### Wiring

1. `AdzunaProvider.search()` — wrap the `httpx.get` path.
2. `JoobleProvider.search()` — wrap the `httpx.post` path.
3. `EmbeddingService.embed_text()` and `embed_batch()` — wrap each `asyncio.to_thread` Voyage AI call.

### 4xx vs. 5xx distinction

4xx HTTP responses indicate a client error (bad query, auth), not a service outage. They are caught *inside* the circuit breaker context so `__aexit__` sees `exc_type=None` (success) and does not increment the failure counter. 5xx responses and `httpx.RequestError` propagate through `__aexit__`, recording a failure.

### fail_open semantics

`CircuitBreaker(fail_open=True)` (the default) silently skips Redis reads/writes when Redis is unavailable, allowing the call to proceed as if the circuit were CLOSED. This is the correct behavior until OPS-4 is resolved: a missing Redis instance must not block job search or embedding.

## Alternatives Considered

**Park — defer to Sprint-44**
Rejected. The implementation is production-ready; `fail_open=True` eliminates the OPS-4 blocker. Parking delays the resilience benefit for no engineering gain, and extended provider outages remain a live risk in Sprint-43.

**Delete — rely on SDK-level retries and existing error handling**
Rejected. SDK retries do not short-circuit failed connections — they compound event-loop pressure during outages. The existing `except httpx.RequestError: return []` path degrades correctly but serially; the circuit provides a sub-millisecond fast-fail path that no SDK retry strategy can replicate.

**Single aggregator-level breaker instead of per-provider**
Considered for simplicity. Rejected because a shared breaker conflates independent providers: an Adzuna outage would suppress Jooble results. Per-provider isolation is worth the minor added cost, especially since Jooble is a fallback source.

## Consequences

**Positive**
- Sustained outages fail fast (< 1 ms after threshold) instead of blocking for up to 30 s per request.
- Adzuna and Jooble circuit states are independent — one provider's failure does not degrade the other.
- `fail_open=True` makes Redis a soft dependency: the system stays operational before OPS-4 lands.

**Negative / trade-offs**
- Redis is now on the critical path for circuit state durability. Mitigated by `fail_open`.
- Per-provider circuit instances share Redis-backed state cluster-wide. A flapping provider trips the circuit for all replicas simultaneously. This is intentional: it prevents thundering-herd re-tries during recovery.
- `embed_batch()` aborts the entire batch if the circuit opens mid-loop. Partial embeddings are not returned. Callers must handle `RuntimeError` and retry the full batch after the recovery window.

**Operational impact**
- OPS-4 must be resolved for circuit state to persist across replica restarts.
- Monitor `pathforge:circuit:adzuna`, `pathforge:circuit:jooble`, `pathforge:circuit:voyage` Redis keys in production.
- Default `recovery_timeout=300 s` and `failure_threshold=3` can be tuned at construction time if provider SLAs change.

## Verification

- `grep -r "CircuitBreaker(" apps/api/` must return hits in `adzuna.py`, `jooble.py`, `embeddings.py`.
- Integration test (fail-open): mock Redis as unavailable → assert `AdzunaProvider.search()` returns a list (not a Redis error).
- Integration test (trip): mock Adzuna to return HTTP 500 three consecutive times → assert the fourth call returns `[]` without hitting the network → assert a call after `recovery_timeout` sends a real request (HALF_OPEN probe).
- Integration test (4xx does not trip): mock Adzuna to return HTTP 400 → assert circuit remains CLOSED after the call.

## References

- Circuit breaker class: `apps/api/app/core/circuit_breaker.py`
- Callers: `apps/api/app/jobs/providers/adzuna.py`, `apps/api/app/jobs/providers/jooble.py`, `apps/api/app/ai/embeddings.py`
- Redis TLS reconciliation: `apps/api/app/core/redis_ssl.py` (ADR-0002)
- Production readiness tracker: `MASTER_PRODUCTION_READINESS.md` § P2-3
- OPS-4 (Redis production provisioning): MASTER_PRODUCTION_READINESS.md § OPS-4
