# ADR-0001: Database SSL secure-by-default with production guard

- **Status**: Accepted
- **Date**: 2026-04-23
- **Deciders**: emre@pathforge.eu (Staff Engineer), Anthropic Claude (Senior Staff review)
- **Context links**:
  - [docs/MASTER_PRODUCTION_READINESS.md](../MASTER_PRODUCTION_READINESS.md) — finding N-1 and OPS-5
  - [apps/api/app/core/config.py](../../apps/api/app/core/config.py)
  - [apps/api/app/core/database.py](../../apps/api/app/core/database.py)
  - [apps/api/alembic/env.py](../../apps/api/alembic/env.py)

## Context

PathForge's only production database is Supabase PostgreSQL, reachable only
over the public internet. The application must negotiate TLS for every
connection. Prior to this decision the configuration was:

```python
database_ssl: bool = False   # Enable for Supabase production
```

with an environment variable `DATABASE_SSL` expected to be set to `true` on
Railway. Three failure modes followed:

1. **Missing env var → plaintext in production.** A misconfigured or reset
   Railway environment would silently connect over plaintext. asyncpg does not
   log the handshake; queries succeed; nothing alerts.
2. **Operator sets `DATABASE_SSL=false` to debug a cert issue**, forgets to
   revert → plaintext persists.
3. **`alembic upgrade head` connects without TLS regardless of the app
   setting.** `alembic/env.py` creates its own async engine via
   `async_engine_from_config` and never consulted the SSL builder. Migrations
   — which carry schema DDL — traversed the public internet unencrypted.

Supabase uses certificates from a public CA (Let's Encrypt chain); Python's
default CA bundle validates them without pinning. There is no compatibility
obstacle to making TLS mandatory.

The audit trail also surfaced that `DATABASE_URL` copied from Supabase's
dashboard sometimes contains `?sslmode=require` or `?ssl=true` as a query
parameter. asyncpg honours both the URL param and the `connect_args={"ssl":
...}` kwarg; the precedence is version-dependent and combining them can raise
`InvalidArgumentError`. Users should not have to think about that interaction.

## Decision

We enforce a **layered secure-by-default** posture on the
`database_ssl` setting:

1. **Auto-derive from environment.** When `DATABASE_SSL` is unset:
   - `environment=production` → TLS **on**.
   - All other environments → TLS off.
2. **Hard guard against downgrade in production.** `ENVIRONMENT=production`
   combined with explicit `DATABASE_SSL=false` is treated as a configuration
   bug; the application raises `ValueError` at `Settings` instantiation and
   the process exits before accepting traffic.
3. **TLS context is hardened.** We require `CERT_REQUIRED`, `check_hostname
   = True`, and `minimum_version = TLSv1_2`.
4. **`DATABASE_URL` SSL query parameters are stripped** with a warning log.
   The sole control surface for TLS is `DATABASE_SSL`.
5. **Migrations traverse the same path.** `alembic/env.py` passes the
   shared `build_connect_args()` output to its async engine.
6. **Runtime verification.** `/api/v1/health/ready` reports the effective
   `ssl` and `ssl_cipher`. Sentry carries a `db.ssl` tag on every event.
7. **No break-glass knob.** If TLS must be disabled in an emergency, revert
   the validator commit and redeploy (~8 minutes). We intentionally refuse to
   ship a `DATABASE_SSL_ALLOW_PLAINTEXT_IN_PROD` switch.

## Alternatives Considered

### A. Flip the default to `True` and rely on `DATABASE_SSL=false` for local dev

Rejected. Breaks every developer machine on the next pull; shifts the failure
from production to dev boxes. Does not defend against explicit-false in prod.

### B. Environment-aware default, no guard

Rejected. Solves the "forgotten env var" case but leaves the "operator sets
false to debug" case unsolved. Guardless defaults are not a Tier-1 posture.

### C. Hard default `True` + production guard, no environment awareness

Rejected. Forces every local dev and every CI job to set `DATABASE_SSL=false`
explicitly. Toil without payoff; the failure-to-set case is not security-
relevant in dev.

### D. Add a `DATABASE_SSL_ALLOW_PLAINTEXT_IN_PROD` break-glass knob

Rejected. Break-glass knobs for security posture are always used eventually,
usually at 2 a.m. during an incident when the reviewer is half-asleep. An
incident where 8 minutes of plaintext is acceptable but 0 minutes is not does
not exist in realistic threat models. The revert-and-redeploy path is the
correct emergency procedure; documenting it in this ADR is our commitment.

### E. Pin the Supabase CA (certificate pinning)

Rejected. Supabase rotates its CA on its own schedule; pinning creates an
operational trap that trades a rare confidentiality risk (CA compromise) for a
common availability risk (rotation breaks us). Python's default CA bundle
validating against a public CA chain is the right layer of trust.

## Consequences

### Positive
- TLS cannot be silently disabled in production. The process refuses to boot
  and logs a clear reason.
- Contributors do not need to read a runbook to understand the correct value
  for `DATABASE_SSL` — they should not set it at all.
- Alembic migrations, application queries, and the readiness probe all use
  the same TLS context — no divergent paths to debug.
- `DATABASE_URL` becomes a pure connection target; SSL is controlled in one
  place.
- Post-mortem tooling improves: Sentry filters can answer "was TLS on?" in
  seconds via the `db.ssl` tag.

### Negative / trade-offs
- Local Postgres without TLS continues to work, but a developer who sets
  `ENVIRONMENT=production` on their laptop (to reproduce a prod bug) now has
  to also set `DATABASE_SSL` correctly or override it. Acceptable.
- Stripping SSL params from `DATABASE_URL` is lossy. If a future provider
  uses URL-carried SSL options for a non-Supabase reason, we will need to
  revisit. Low probability.
- One-line revert exists but requires code+deploy, not just an env change.
  This is intentional; the friction is the feature.

### Operational impact
- Railway: `DATABASE_SSL` is no longer a required variable. It *may* still be
  set explicitly for belt-and-suspenders verification.
- `alembic upgrade head` invoked via the Railway shell now runs over TLS.
- `/api/v1/health/ready` emits `db.ssl` and `ssl_cipher` fields; UptimeRobot
  (OPS-6) can assert on these in its response-body check.

## Verification

A regression is impossible only if we test it, so:

1. **Unit tests** (`apps/api/tests/test_config_database_ssl.py`):
   - All 18 cells of the (`environment`, explicit-bool, url-ssl-param) matrix.
   - `ENVIRONMENT=production` + `DATABASE_SSL=false` raises `ValueError`.
   - `DATABASE_URL` ssl query params are stripped with a warning.
2. **Connect-args tests** (`apps/api/tests/test_database_connect_args.py`):
   - SSL context is `CERT_REQUIRED`, hostname-checked, TLS 1.2+.
   - Empty dict when SSL off.
3. **Boot-time guard job** in CI (`config-guards`):
   - `ENVIRONMENT=production` + unset `DATABASE_SSL` → `settings.database_ssl
     is True`.
   - `ENVIRONMENT=production` + `DATABASE_SSL=false` → process exits non-zero.
4. **Post-deploy smoke**:
   - `curl https://api.pathforge.eu/api/v1/health/ready | jq .db` shows
     `"ssl": true` and a modern cipher.
   - Railway shell: `SELECT ssl_is_used();` returns `t`.
5. **Sentry**: `db.ssl:true` tag visible on at least one event within 10
   minutes of deploy.

## References

- [apps/api/app/core/db_ssl.py](../../apps/api/app/core/db_ssl.py) —
  TLS context builder.
- [apps/api/tests/test_config_database_ssl.py](../../apps/api/tests/test_config_database_ssl.py)
- [apps/api/tests/test_database_connect_args.py](../../apps/api/tests/test_database_connect_args.py)
- [.github/workflows/ci.yml](../../.github/workflows/ci.yml) —
  `config-guards` job.
- CPython docs: `ssl.create_default_context`,
  [PEP 644](https://peps.python.org/pep-0644/) (TLS 1.2 floor in default
  context).
- asyncpg docs: `ssl` parameter behaviour and URL precedence.
