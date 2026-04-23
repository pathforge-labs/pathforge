# ADR-0002: Redis SSL secure-by-default with production guard and scheme reconciliation

- **Status**: Accepted
- **Date**: 2026-04-23
- **Deciders**: emre@pathforge.eu (Staff Engineer), Anthropic Claude (Senior Staff review)
- **Context links**:
  - [ADR-0001](0001-database-ssl-secure-by-default.md) — parent pattern
  - [docs/MASTER_PRODUCTION_READINESS.md](../MASTER_PRODUCTION_READINESS.md) — finding N-1b, OPS-4
  - [apps/api/app/core/redis_ssl.py](../../apps/api/app/core/redis_ssl.py)
  - [apps/api/app/core/config.py](../../apps/api/app/core/config.py)

## Context

PathForge uses Redis for five production-critical purposes, all of which
carry data whose integrity and confidentiality matter:

1. **JWT token blacklist** (`token:blacklist:*` keys): revocation state.
   An attacker who can read it learns which tokens are revoked; an attacker
   who can write it can **unrevoke** a stolen token.
2. **Rate limit counters** (slowapi storage): brute-force protection.
3. **Circuit-breaker state** (planned consumers): external-service health.
4. **LLM budget guard**: monthly spend cap against runaway models.
5. **ARQ job queue**: background job names and payloads (may include
   application data).

Prior to this decision, `redis_ssl: bool = False` defaulted to plaintext.
Three design-level defects existed:

- **No environment-aware default**. The same pattern ADR-0001 closed
  for PostgreSQL (auto-derive TLS from `ENVIRONMENT=production`) was
  absent for Redis.
- **One latent plaintext bug**. [app/core/llm.py:112](../../apps/api/app/core/llm.py#L112)
  (LLM budget guard) passed `settings.redis_url` to
  `aioredis.from_url()` without consulting `settings.redis_ssl`. With
  `redis_ssl=True` configured, token blacklist + rate-limit travelled
  over TLS while LLM budget tracking travelled plaintext — a partial
  rollout that silently splits the TLS posture.
- **Duplicated URL rewriting**. `token_blacklist.py`, `rate_limit.py`,
  and `worker.py` each re-implemented the `redis://` → `rediss://`
  scheme rewrite against `settings.redis_ssl`. Three independent
  copies of the same logic — one of them drifting was inevitable.

The scope of remediation is therefore wider than ADR-0001: this ADR not
only establishes the secure-by-default posture, it also consolidates the
five consumers onto a single helper and closes the latent bug.

## Decision

We apply a **layered secure-by-default posture** to Redis, parallel to
ADR-0001 but tailored to Redis's two API shapes (URL-based and
ARQ-`RedisSettings`-based):

1. **Auto-derive from environment.** When `REDIS_SSL` is unset:
   - `environment=production` → TLS **on** (`True`).
   - All other environments → TLS off (`False`).
2. **Hard guard against downgrade in production.** `ENVIRONMENT=production`
   combined with explicit `REDIS_SSL=false` raises `ValueError` at
   `Settings()` construction and the process exits before accepting
   traffic. Same posture as ADR-0001's DB guard.
3. **Scheme–flag reconciliation is upgrade-only.** The `REDIS_URL` scheme
   and the `REDIS_SSL` flag can each carry TLS intent. When they disagree:
   - `redis://` + flag `True` → **upgrade** the scheme to `rediss://`,
     log a static-string WARNING (no DSN interpolation).
   - `rediss://` + flag `False`:
     - **In production** → `ValueError` at boot (scheme is stricter
       than flag; downgrade is the dangerous direction).
     - **In development/testing** → scheme wins, flag is upgraded to
       `True`, log a WARNING.
   - Concordant cases are no-ops.
4. **One shared helper module.** All five consumers (four active + one
   future/docstring) route through `app/core/redis_ssl.py`:
   - `resolve_redis_url(url, ssl_enabled, environment) -> str` — applies
     the reconciliation rules above and returns the canonical URL.
   - `arq_ssl_flag(ssl_enabled) -> bool` — one-line wrapper for the ARQ
     path's `RedisSettings(ssl=...)` shape.
5. **TLS context is idiomatic**, not custom. redis-py 5.3.1 (our floor
   `>=5.2.0`) parses `rediss://` and automatically sets
   `ssl_cert_reqs='required'` + `ssl_check_hostname=True`. We do NOT
   pass explicit `ssl_cert_reqs`/`ssl_check_hostname` kwargs — that
   would introduce a second control surface (the exact footgun ADR-0001
   §G2 warned about). The URL scheme is the sole control surface for
   URL-based callers.
6. **Runtime verification via client-side introspection.**
   `/api/v1/health/ready` reports the effective Redis TLS posture by
   inspecting the Python client's connection class
   (`isinstance(pool.connection_class, SSLConnection)`) — zero network
   round-trips. No `CLIENT INFO` command; no DoS-amplifier vector. The
   cached TTL pattern from ADR-0001 is unnecessary because the check
   is constant-time.
7. **Sentry tagging parity.** `redis.ssl` joins `db.ssl` as a global
   tag set once in the lifespan, using the same init-state gate.
8. **No break-glass knob.** Same doctrine as ADR-0001 Alternative D —
   the emergency path is revert-and-redeploy. Break-glass knobs for
   security posture are always used eventually.

## Alternatives Considered

### A. Apply ADR-0001 pattern mechanically; leave the 5-site duplication

Rejected. Misses the consolidation win. Three existing sites + one future
site would keep drifting. And it does not close the latent llm.py bug —
that file does not route through any of the duplicated sites.

### B. Deprecate `REDIS_SSL`; require `rediss://` scheme in `REDIS_URL`

Rejected. Most idiomatic in the Redis ecosystem, but:
- Breaks back-compat for operators who already set `REDIS_SSL=true`.
- ARQ's `RedisSettings(ssl=bool, host=..., port=...)` takes the boolean
  directly, not a URL. The flag still exists for that path regardless
  of what we do with the URL path.

### C. Rely purely on scheme (`rediss://`)

Rejected for the same reason as B — conflicts with ARQ's parameter
shape.

### D. Add a `DATABASE_SSL_ALLOW_PLAINTEXT_IN_PROD`-style break-glass
    knob for Redis

Rejected. Same argument as ADR-0001 §D: break-glass knobs for security
posture are always used eventually, usually at 2 a.m. during an incident
when the reviewer is half-asleep. Revert-and-redeploy takes ~8 minutes;
an incident where 8 minutes of plaintext is acceptable but 0 minutes is
not does not exist in realistic threat models.

### E. Pin a specific CA bundle for Redis

Rejected. Same reasoning as ADR-0001 §E: public CA rotation is a common
availability risk; CA compromise is a rare confidentiality risk. Python's
default CA bundle validating against a public CA chain is the right trust
model for Upstash and Railway's managed Redis.

### F. Server-side TLS attestation via `CLIENT INFO`

Rejected. Would add a second Redis round-trip on every `/health/ready`
hit — the exact DoS-amplifier pattern ADR-0001 closed via 60s TTL caching.
Client-side connection-class introspection is constant-time and sufficient.

## Consequences

### Positive

- Redis TLS cannot be silently disabled in production. Process fails
  boot with a clear reason.
- Contributors do not need to read a runbook to understand `REDIS_SSL`
  — they should not set it at all.
- One helper, one test surface. Adding a sixth Redis consumer means
  calling one function, not re-implementing the reconciliation logic.
- LLM budget guard is no longer the weakest link in the TLS rollout.
- `/health/ready` attestation adds zero network cost — client-side
  introspection only.
- Post-mortem tooling improves: Sentry filter `redis.ssl:true` answers
  "was Redis TLS on when the incident occurred?" in one click.

### Negative / trade-offs

- A sixth Redis consumer that imports `redis.asyncio.Redis` directly
  (without calling the helper) re-opens the drift. Mitigated by a grep
  regression: CI check asserts that every `Redis.from_url` call in
  `app/` outside the helper module is explicitly exempted with a code
  comment.
- The `rediss://` + `ssl_enabled=False` conflict in dev promotes the
  flag silently (scheme wins). An operator who expected the flag to be
  honoured gets a WARNING log line rather than a failure. Accepted
  because dev/test is not a confidentiality-sensitive environment.

### Operational impact

- Railway: `REDIS_SSL` is no longer a required variable. Setting it
  explicitly is belt-and-suspenders.
- When OPS-4 provisions Redis, the **provider must accept TLS on the
  wire** (Upstash always does; Railway Redis plugin does when configured
  for it). A plaintext provider with `rediss://` scheme will fail the
  handshake — a loud failure, not a silent downgrade. Prefer Upstash or
  TLS-enabled Railway Redis.
- `/api/v1/health/ready` emits a new structured `redis_detail` block:
  `{"status", "ssl", "ssl_attested", "scheme"}`. The legacy `redis`
  string key is preserved for back-compat (same convention as
  `database` + `db` from ADR-0001). UptimeRobot body-checks can assert
  on either surface.

### Operational impact — future extension point

If PathForge ever adds an internal-VPC Redis with a private CA, the
helper's signature already accepts extension — add an optional
`ssl_ca_certs: str | None = None` kwarg. No action today; public CA
covers Upstash and Railway's managed offerings.

## Verification

1. **Unit tests** (`apps/api/tests/test_redis_ssl.py`, `test_config_redis_ssl.py`):
   - All reconciliation cells (scheme × flag × environment).
   - `ENVIRONMENT=production` + `REDIS_SSL=false` raises `ValueError`.
   - `ENVIRONMENT=production` + `REDIS_URL=rediss://…` + `REDIS_SSL=false`
     raises `ValueError`.
   - Non-scheme URL components (userinfo, path, port, db-number,
     query params) preserved byte-for-byte.
   - Idempotency: `resolve(resolve(url, True), True) == resolve(url, True)`.
   - DSN-leak regression: WARNING log lines contain no user/password/host.
2. **Latent-bug closure tests** (`test_llm_redis_ssl.py`):
   - Spy on `app.core.llm.aioredis.from_url` → assert TLS scheme reaches
     it when `settings.redis_ssl_enabled=True`.
3. **Boot-time config-guards job** (CI):
   - prod + unset `REDIS_SSL` → `settings.redis_ssl_enabled is True`.
   - prod + `REDIS_SSL=false` → process exits non-zero.
   - prod + `REDIS_URL=rediss://…` + `REDIS_SSL=false` → process exits
     non-zero.
4. **Post-deploy smoke** (once OPS-4 provisions Redis):
   - `curl /api/v1/health/ready | jq .redis_detail` shows
     `"ssl": true, "ssl_attested": true, "scheme": "rediss"`.
   - Sentry `redis.ssl:true` tag visible on at least one event within
     10 minutes of deploy.

## References

- [ADR-0001](0001-database-ssl-secure-by-default.md) — parent pattern.
- [apps/api/app/core/redis_ssl.py](../../apps/api/app/core/redis_ssl.py) —
  shared helper.
- [apps/api/tests/test_redis_ssl.py](../../apps/api/tests/test_redis_ssl.py)
- [apps/api/tests/test_config_redis_ssl.py](../../apps/api/tests/test_config_redis_ssl.py)
- [apps/api/tests/test_llm_redis_ssl.py](../../apps/api/tests/test_llm_redis_ssl.py)
- redis-py docs: `Redis.from_url` scheme parsing, `SSLConnection` class.
- ARQ docs: `RedisSettings(ssl=...)`.
