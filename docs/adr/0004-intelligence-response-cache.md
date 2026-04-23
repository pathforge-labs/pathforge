# ADR-0004: Redis-Backed Intelligence Response Cache with Fail-Open Semantics

- **Status**: Accepted
- **Date**: 2026-04-23
- **Deciders**: Senior Staff Engineer (PathForge quality-playbook authority)
- **Context links**: [ADR-0002](0002-redis-ssl-secure-by-default.md), [ADR-0003](0003-circuit-breaker-adopted-for-external-apis.md), MASTER_PRODUCTION_READINESS.md § D7 Performance, Sprint-43/44

---

## Context

PathForge exposes 12 intelligence engine dashboards via GET endpoints:

| Engine | Endpoint | Computation cost |
|:--|:--|:--|
| Career DNA | `GET /api/v1/career-dna` | Full LLM analysis + 5 DB relation loads |
| Threat Radar | `GET /api/v1/threat-radar` | DB aggregation + market signal assembly |
| Salary Intelligence | `GET /api/v1/salary-intelligence` | Salary range + skill impact + trajectory |
| Skill Decay | `GET /api/v1/skill-decay` | Freshness decay computation + pathway assembly |
| Recommendation Intelligence | `GET /api/v1/recommendations/dashboard` | Cross-engine correlation + status aggregation |

All five dashboard GETs are compute-heavy on the cold path (LLM calls, multi-relation DB loads, aggregation). The typical user opens the dashboard repeatedly during a session — daily, or multiple times per day — but the underlying data only changes when the user explicitly triggers a scan (`POST /scan`, `POST /generate`) or performs a targeted mutation (confirm hidden skill, refresh skill, update target role, etc.).

Without caching:
- Every dashboard GET triggers full LLM + DB computation (1–3 s cold).
- Concurrent requests from the same user (e.g., page refresh) can fan into multiple simultaneous expensive operations.
- The dashboard feels slow even when the data hasn't changed.

### Constraints inherited from ADR-0002 / ADR-0003

Redis is not yet provisioned in production (OPS-4). Any Redis-dependent feature must degrade gracefully when Redis is unavailable — the same `fail_open` philosophy established for the circuit breaker in ADR-0003.

### Scope of this ADR

This ADR covers only the **GET response cache** layer (read-through, invalidate-on-mutation). It does not cover write-through caching, query-level caching, or LLM prompt caching (those are separate concerns).

---

## Decision

Implement a Redis-backed response cache (`app/core/intelligence_cache.py`, class `IntelligenceCache`, module singleton `ic_cache`) with the following design:

### 1. Cache key structure

```
pathforge:ic:{user_id}:{endpoint_label}
```

Per-user, per-endpoint. Namespace prefix `pathforge:ic` is fixed to enable SCAN-based wildcard invalidation.

### 2. TTL calibration

| Cache constant | Value | Rationale |
|:--|:--|:--|
| `TTL_CAREER_DNA` | 1800 s (30 min) | Changes only on resume upload / dimension regeneration |
| `TTL_THREAT_RADAR` | 3600 s (60 min) | External market data refreshed at most hourly |
| `TTL_SALARY` | 3600 s (60 min) | Same — salary benchmarks are externally sourced |
| `TTL_SKILL_DECAY` | 3600 s (60 min) | Decay is a slow function; freshness changes over days |
| `TTL_RECOMMENDATIONS` | 900 s (15 min) | Job listings change frequently; shorter window acceptable |
| `TTL_DEFAULT` | 1800 s (30 min) | Fallback for unlisted endpoints |

### 3. Fail-open semantics

All Redis operations (`get`, `set`, `invalidate_user`) are wrapped in `try/except`. On any exception (connection error, timeout, serialization failure):
- `get()` returns `None` → route falls through to live computation.
- `set()` is a no-op → route returns the live result uncached.
- `invalidate_user()` is a no-op → stale keys will expire on TTL.

This matches the ADR-0003 circuit breaker philosophy: Redis is a **performance optimisation**, not a correctness dependency. The system degrades to full computation without failing requests.

### 4. SCAN-based invalidation (not KEYS)

`invalidate_user()` uses `r.scan_iter(pattern)` to find and delete all keys matching `pathforge:ic:{user_id}:*`. Redis `SCAN` iterates in O(1) amortised steps per cursor advance and does not block the event loop, unlike `KEYS` which is O(N) and blocks.

### 5. Invalidation triggers

Cache is invalidated by calling `await ic_cache.invalidate_user(current_user.id)` after every mutation that would render any dashboard stale:

| Endpoint | Trigger |
|:--|:--|
| `POST /career-dna/generate` | Full Career DNA regeneration |
| `PUT /career-dna/growth/target-role` | Updates growth_vector embedded in Career DNA response |
| `PATCH /career-dna/hidden-skills/{id}` | Flips `user_confirmed` in skill list |
| `POST /threat-radar/scan` | New scan results |
| `PATCH /threat-radar/alerts/{id}` | Alert status changes `total_unread_alerts` |
| `POST /salary-intelligence/scan` | New salary estimate + impacts |
| `POST /skill-decay/scan` | New freshness + velocity + pathways |
| `POST /skill-decay/refresh` | Resets a skill's freshness score |
| `POST /recommendations/generate` | New recommendation batch |
| `PUT /recommendations/{id}/status` | Status transitions affect dashboard counters |

Invalidation is deliberately broad (whole-user) rather than key-specific. The cost of a slightly over-eager invalidation (a few extra DB calls) is far lower than the complexity of tracking fine-grained dependencies between mutations and cached fields.

### 6. Serialisation

Cache values are stored as `json.dumps(response.model_dump(mode="json"))` and deserialized with `json.loads` → `ResponseModel.model_validate(cached)`. Pydantic `model_dump(mode="json")` ensures datetime/UUID types are serialized to strings.

### 7. Route pattern

```python
cache_key = ic_cache.key(current_user.id, "career_dna")
cached = await ic_cache.get(cache_key)
if cached is not None:                         # ← None check, not truthiness
    return CareerDNAResponse.model_validate(cached)

result = _build_full_response(career_dna)
await ic_cache.set(cache_key, result.model_dump(mode="json"), ttl=ic_cache.TTL_CAREER_DNA)
return result
```

The `is not None` check (not `if cached`) is intentional: an empty dict `{}` is a valid cached response and must not be treated as a cache miss.

---

## Alternatives Considered

### A. In-process LRU cache (`functools.lru_cache` / `cachetools.TTLCache`)

**Rejected.** PathForge runs multiple Railway instances. An in-process cache is per-instance; a scan result cached on instance A is not visible on instance B. A user round-robined across instances would see misses on most requests. Additionally, in-process caches consume process memory proportional to the number of users × cached response size, with no eviction visibility. Redis provides a shared, observable, TTL-enforced store across all instances.

### B. CDN edge cache (Cloudflare, Vercel Edge Network)

**Rejected.** All five dashboard endpoints require a user-authenticated JWT (`Authorization: Bearer ...`). CDN edge caches cannot differentiate per-user responses on the same URL path without per-user cache keys (which require paid CDN features) and expose a risk of serving one user's data to another if misconfigured. Edge caches are appropriate for public, unauthenticated content — not private dashboard data.

### C. Database-level result caching (materialized views, pg_stat_statements)

**Rejected.** The compute cost is not primarily in the SQL queries — it is in the LLM inference calls and response assembly (building Pydantic trees from ORM relations). Materializing SQL results does not eliminate the LLM or the serialisation overhead. Additionally, Supabase/RDS materialized views refresh on schedule rather than on mutation, making invalidation coordination harder.

### D. No cache (status quo)

**Rejected.** Benchmark observation: Career DNA GET on cold path takes 1–3 s under LLM load. A user opening the dashboard three times in a session makes three full LLM round-trips. Under concurrent sessions this amplifies. The 30-min TTL means a user who does not trigger a new scan receives sub-100ms responses for all subsequent dashboard views — a 10–30× improvement.

---

## Consequences

### Positive

- Dashboard GETs on cache-warm path: expected p95 < 100 ms (from 1–3 s cold).
- Reduces LLM API spend (fewer redundant recomputations).
- Reduces Supabase connection pressure during traffic bursts.
- Fail-open design means Redis provisioning (OPS-4) is not a launch blocker.

### Negative / Trade-offs

- **Stale window**: A user who mutates data outside the defined invalidation triggers (e.g. via a direct DB update in a future admin endpoint) will see stale dashboard data until TTL expiry. Any new mutating endpoint added in future must include `await ic_cache.invalidate_user(current_user.id)` — enforced by code review policy, not by automated tooling.
- **Cache warming latency**: First request after TTL expiry or invalidation pays full cold-path cost. Under high traffic this creates a "thundering herd" when many users' caches expire simultaneously. Mitigation: jittered TTLs can be added if this becomes observable (not implemented now — premature).
- **Redis key sprawl**: Each user × endpoint pair is a key. At 10,000 users × 5 endpoints = 50,000 keys — well within Redis capacity limits.
- **Serialization fidelity**: `model_dump(mode="json")` converts datetimes to ISO strings and UUIDs to str. `model_validate` reverses this via Pydantic validators. Any future schema change that cannot round-trip through JSON must account for cache invalidation.

### Operational Impact

- Requires Redis (OPS-4). Without Redis, all cache operations are no-ops (fail-open).
- Monitor cache hit rate via `redis-cli MONITOR` or `INFO keyspace`.
- `invalidate_user()` logs key deletions at `INFO` level — visible in Railway logs.
- Cache can be fully flushed per-user in a support incident: `redis-cli DEL $(redis-cli KEYS "pathforge:ic:{user_id}:*")`.

---

## Verification

| Check | How |
|:--|:--|
| Cache hit serves stale-free data after mutation | `test_roundtrip_set_get_invalidate` + route-level invalidation tests |
| Fail-open: Redis unavailable → request succeeds | `test_get_redis_unavailable_returns_none`, `test_set_redis_unavailable_is_noop`, `test_invalidate_user_redis_unavailable_is_noop` |
| `is not None` check (not truthiness) | `test_get_hit_empty_dict_is_not_none` |
| TTL applied correctly | `test_set_applies_correct_ttl_per_type` |
| Key prefix correct for SCAN | `test_key_prefix_matches_scan_pattern` |
| Invalidation on scan completion | Manual: run `POST /scan`, verify old cached key deleted (Redis monitor), verify new GET returns fresh data |
| Cache-warm p95 < 100 ms | `bash scripts/perf-baseline.sh` after OPS-4 provisioned; results in `docs/baselines/api-*.csv` |

---

## References

- Implementation: `apps/api/app/core/intelligence_cache.py`
- Route integrations: `apps/api/app/api/v1/{career_dna,threat_radar,salary_intelligence,skill_decay,recommendation_intelligence}.py`
- Tests: `apps/api/tests/test_intelligence_cache.py`
- Performance baseline script: `scripts/perf-baseline.sh`
- [ADR-0002](0002-redis-ssl-secure-by-default.md) — Redis TLS (same Redis instance)
- [ADR-0003](0003-circuit-breaker-adopted-for-external-apis.md) — `fail_open` pattern origin
