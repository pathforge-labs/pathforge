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

---

## Corrigendum (2026-05-08): Pooler chain rooted at Supabase-private CA

### What was wrong

The original ADR (§"Context", final paragraph) stated:

> Supabase uses certificates from a public CA (Let's Encrypt chain);
> Python's default CA bundle validates them without pinning.

This is **true for direct DB endpoints** (`db.<ref>.supabase.co`) but
**false for Supavisor pooler endpoints** (`*.pooler.supabase.com`).
The pooler chain was empirically probed on 2026-05-08:

```
depth=0  CN=*.pooler.supabase.com
         issued by: Supabase Intermediate 2021 CA
depth=1  CN=Supabase Intermediate 2021 CA
         issued by: Supabase Root 2021 CA
depth=2  CN=Supabase Root 2021 CA               ← self-signed
         O=Supabase Inc, C=US
         valid 2021-04-28 → 2031-04-26
         SHA-256: 80:70:25:AD:50:D4:ED:21:9D:2C:9C:7D:29:9C:00:4F:
                  82:4E:B0:0C:F7:F6:5A:FE:F6:07:D0:7B:72:E6:CA:FA
```

The root is **not** in Mozilla's trust store, **not** in any distro
bundle, and **not** in `certifi`. OpenSSL rejects every chain probe with
`X509_V_ERR_SELF_SIGNED_CERT_IN_CHAIN` (error 19) under any standard
public bundle. This caused every production `alembic upgrade head` to
fail at TLS handshake, blocking deploys for five days
(2026-05-03 → 2026-05-08; tracked in issue #49).

The intermediate failure attempt — pinning to `certifi.where()` (commit
`ac3eba9`, PR #57) — moved the trust store from the system bundle to
the Mozilla bundle but did not change the fundamental gap: Mozilla also
does not include the Supabase-private root.

### What changes

Alternative E ("Pin the Supabase CA") was previously rejected on the
grounds that "Supabase rotates its CA on its own schedule; pinning
creates an operational trap that trades a rare confidentiality risk (CA
compromise) for a common availability risk (rotation breaks us)". This
rationale was based on an **incorrect premise** — there is no public
chain to fall back to for the pooler endpoint, so we are not "trading"
anything; we are simply choosing whether to verify or not. The actual
trade is: pin the private root explicitly, or disable chain verification
entirely (downgrade to encryption-only, vulnerable to active MITM).

**Updated decision (supersedes Alternative E rejection for the pooler
case)**: vendor `Supabase Root 2021 CA` into the repo as
`apps/api/certs/supabase-prod-ca-2021.crt` and load it via
`SSLContext.load_verify_locations()` **in addition to** the Mozilla
bundle. The trust store becomes the union — covering the pooler (private
root), the direct DB (Let's Encrypt), and any future non-Supabase
provider, without taking anything off the table.

This is not "certificate pinning" in the strict HPKP sense — we still
trust whatever cert Supabase happens to issue, as long as it chains to
the 2021 root. We are not pinning the leaf cert or its public key.

### Rotation playbook (action: 2031-04-26 minus 90 days)

The vendored root expires `2031-04-26 10:56:53 UTC`. Set a calendar
reminder for **2031-01-26** (90-day buffer):

1. Check Supabase dashboard → Database Settings → SSL Configuration for
   a new "Download CA cert" link (the Supabase CLI's
   `internal/gen/types/templates/prod-ca-2021.crt` will likely be
   renamed to `prod-ca-2031.crt` or similar at the same time).
2. Probe the live pooler:
   `echo | openssl s_client -showcerts -servername aws-0-eu-west-1.pooler.supabase.com -connect aws-0-eu-west-1.pooler.supabase.com:5432 -starttls postgres 2>&1 | openssl x509 -noout -issuer -subject -dates -fingerprint -sha256`
   Confirm the root subject and SHA-256 match the new bundle.
3. Replace `apps/api/certs/supabase-prod-ca-2021.crt` with the new
   cert. (Do not delete the old one in the same PR — keep both in the
   bundle for ~30 days during overlap, then drop the expired one.)
4. Update the SHA-256 in `app/core/db_ssl.py` header comment.
5. Bump the constant `SUPABASE_ROOT_CN` in
   `tests/test_database_connect_args.py` if the CN changes.
6. Deploy via the standard production promotion path; verify
   `/api/v1/health/ready` returns `db.ssl: true` post-deploy.

If Supabase rotates earlier than expected (out-of-band), the same
procedure applies — the trigger is the live probe diverging from the
vendored root, not the calendar.

### Verification (additions to original §Verification)

6. **Trust-store regression tests**
   (`tests/test_database_connect_args.py`):
   - `test_ssl_context_loads_supabase_private_root` — fails if the
     vendored bundle is missing or no longer carries
     `Supabase Root 2021 CA`.
   - `test_supabase_ca_bundle_file_exists` — fails if the cert file is
     not shipped with the source tree.
   - `test_missing_supabase_bundle_raises_loudly` — confirms
     `build_connect_args` raises `FileNotFoundError` rather than
     silently downgrading.

7. **Container-layout assertion** — the Dockerfile must `COPY apps/api/
   certs ./certs` so `Path(__file__).resolve().parents[2] / "certs"`
   resolves at both build-time and runtime. Validated by the
   post-deploy smoke probe (`/api/v1/health/ready` returns 200) which
   only succeeds if alembic completed, which only succeeds if the
   bundle was found.

### References (additions)

- Live cert probe (2026-05-08): see GitHub issue #49 thread for the
  full `openssl s_client -showcerts` output.
- Canonical CA download URL:
  `https://raw.githubusercontent.com/supabase/cli/main/internal/gen/types/templates/prod-ca-2021.crt`
  (embedded by `supabase/cli` at
  `internal/gen/types/templates/prod-ca-2021.crt`).
- Supabase docs: [Postgres SSL Enforcement](https://supabase.com/docs/guides/platform/ssl-enforcement) — describes the dashboard download path.
- asyncpg `ssl` precedence:
  [asyncpg #737](https://github.com/MagicStack/asyncpg/issues/737),
  [SQLAlchemy #6275](https://github.com/sqlalchemy/sqlalchemy/issues/6275)
  — confirms `connect_args={"ssl": SSLContext}` is the canonical path
  and that URL `?sslmode=` parameters must be stripped (already done
  per ADR §Decision item 4).
