# Runbook — Secret Rotation

> **When to use**: scheduled rotation (quarterly), suspected compromise,
> staff offboarding who had access to a secret, or before any
> production deployment that changes trust boundaries.
> **Primary owner**: security@pathforge.eu.
> **SLO**: routine rotation ≤ 1 hour end-to-end; suspected compromise ≤ 15 minutes to revoke + ≤ 1 hour to fully rotate.

---

## 0. Rotation calendar (routine)

| Secret | Target cadence | Surface | Criticality if compromised |
| :--- | :--- | :--- | :--- |
| `JWT_SECRET` + `JWT_REFRESH_SECRET` | Quarterly | Token signing keys | **CRITICAL** — attacker can forge access/refresh tokens for any user |
| `STRIPE_SECRET_KEY` | Rotate via Stripe Dashboard when a staff member leaves | Payment API | **CRITICAL** — attacker can charge/refund/create customers, read full PCI metadata |
| `STRIPE_WEBHOOK_SECRET` | Quarterly | Webhook signature verification | HIGH — attacker can spoof webhook events (subscription state, payment success) |
| `ANTHROPIC_API_KEY` / `GOOGLE_AI_API_KEY` / `VOYAGE_API_KEY` | Quarterly or on suspicion | LLM provider keys | HIGH — cost runaway + prompt history exposure |
| `DATABASE_URL` password | Quarterly (rotate the Supabase service-role password in the dashboard) | DB auth | **CRITICAL** — full data read/write |
| `REDIS_URL` password (if provider supplies one) | Quarterly | Token blacklist + rate-limit + ARQ job payloads | **CRITICAL** — session hijack via un-revoke, job-payload tampering |
| `RESEND_API_KEY` | Quarterly | Transactional email | MEDIUM — spam potential from our domain; SPF/DKIM/DMARC limit blast radius |
| `TURNSTILE_SECRET_KEY` | Annually | CAPTCHA server verification | LOW — captcha is a defence-in-depth layer, not a primary control |
| `GOOGLE_OAUTH_CLIENT_ID` + Microsoft variants | Annually | SSO client IDs (public) + MSFT secret | MEDIUM — SSO redirect/phishing path |
| `SENTRY_DSN` + `NEXT_PUBLIC_SENTRY_DSN` | On compromise only (DSN rotation requires a new project) | Error tracking ingest | LOW — intentionally semi-public; worst case is error-data spam |
| `INITIAL_ADMIN_EMAIL` | Immutable after first boot | Admin promotion seed | n/a — not a secret |

**Incident-driven rotation** overrides the calendar. Any secret suspected
of exposure is rotated immediately per §3.

---

## 1. Pre-rotation checklist

Before rotating anything:

- [ ] Note the start time + who is executing (Slack or incident log).
- [ ] Confirm production deploy is not in progress (`gh run list -R pathforge-labs/pathforge --workflow=deploy.yml --limit 3`).
- [ ] Confirm monitoring is green before the rotation so any step-induced alerts are traceable (`curl https://api.pathforge.eu/api/v1/health/ready`).
- [ ] For JWT/DB/Redis: broadcast a 1-line heads-up in the team channel — these rotations sign-out all users and invalidate in-flight jobs.
- [ ] Have the new secret value generated and available in a secure clipboard (password manager, not shell history).

---

## 2. Rotation procedures per secret

### 2.1 JWT signing secrets (`JWT_SECRET`, `JWT_REFRESH_SECRET`)

**Effect**: every access and refresh token issued under the old keys becomes invalid. All users are signed out.

1. Generate two **distinct** 32-byte keys:
   ```bash
   openssl rand -hex 32  # JWT_SECRET
   openssl rand -hex 32  # JWT_REFRESH_SECRET (must differ — boot guard enforces)
   ```
2. On Railway → `pathforge-api` → Variables:
   - Set `JWT_SECRET` to the first value.
   - Set `JWT_REFRESH_SECRET` to the second.
   - Save → Railway triggers a redeploy.
3. Wait for the new revision to be healthy (`/api/v1/health/ready` → 200).
4. Smoke-test auth: `POST /api/v1/auth/login` with a test account → expect a **new** token. Attempting to use an old token should return 401.
5. Record: rotation time, initiator, why (routine / incident), old-secret last-4-bytes of SHA-256 hash in the security log (so a future incident can correlate).

**Rollback**: re-set the previous secrets and redeploy. All pre-rotation tokens resume working immediately. Acceptable within the same 4-hour window; beyond that the "new" tokens from the rotated window need their own handling.

### 2.2 Database password (Supabase service-role)

**Effect**: active connection pools in API + Alembic will fail on next checkout. Brief read/write outage (~30s).

1. Supabase Dashboard → Project → Settings → Database → "Reset database password" → copy the new password.
2. On Railway → `pathforge-api` → Variables → update the password portion of `DATABASE_URL`. Keep the `postgresql+asyncpg://` scheme; keep host/port/database; if the Supabase dashboard supplies a URL with `?sslmode=require` or similar libpq SSL query params, paste the URL as-is — ADR-0001 strips those params at boot, so no manual edit is needed.
3. Save → Railway redeploys. Monitor `/api/v1/health/ready` → `database.status: connected` within 60s.
4. Any long-running ORM worker that held an open connection on the old password will fail on its next pool checkout and automatically open a new connection against the new password. No manual action needed in the usual case; watch worker logs for ~2 minutes to confirm no stuck-retry loop.

**Rollback**: the old password is invalid after reset. No rollback path exists at the password layer; if the deploy is broken, fix the env var and redeploy. For that reason: always test the new `DATABASE_URL` in the Railway variables preview UI before saving.

### 2.3 Redis password (Upstash / Railway Redis)

**Effect**: token blacklist + rate-limit counters + ARQ job queue temporarily unreachable. Token blacklist is fail-closed in production — auth will reject all requests for the pool-reset window (~15–30 seconds).

1. In the Redis provider dashboard, generate a new password/token.
2. On Railway → `pathforge-api` and `pathforge-worker` → Variables → update `REDIS_URL` with the new credentials. **Scheme note**: ADR-0002 applies upgrade-only reconciliation — if the provider supplies a `redis://` URL, the runtime will auto-upgrade it to `rediss://` in production (warning logged). A `rediss://` URL + `REDIS_SSL=false` override in prod is rejected at boot. Paste the provider URL as-is; do not try to pre-mangle the scheme. Update both services simultaneously.
3. Save both → both redeploy. Monitor `/api/v1/health/ready` → `redis_detail.ssl_attested: true` AND `redis: "connected"`.
4. If rate limit degrades to memory during the window: that is expected; `RATE_LIMIT_DEGRADED` surfaces in readiness. Cleared on next deploy.

**Rollback**: provider-side passwords are usually ephemeral (the "reveal" only works once). Test the new URL in a Railway preview before saving the production env.

### 2.4 Stripe secret key

**Effect**: Stripe's "Roll key" flow requires choosing an **expiry** for the old key at roll-time (1 hour default, up to 7 days). New key activates immediately on Stripe's side; old key auto-expires at the chosen deadline.

1. Stripe Dashboard → Developers → API keys → "Roll key" on the Secret key. At the prompt, choose the **shortest** expiry that lets you redeploy — **1 hour is usually sufficient** and is the default.
2. Copy the new `sk_live_…` value.
3. On Railway → `pathforge-api` → set `STRIPE_SECRET_KEY` to the new value → redeploy.
4. Verify a test charge succeeds (`POST /api/v1/billing/create-checkout-session` on a test account → complete flow → webhook verifies).
5. Old-key expiry is automatic — no manual revoke step. Confirm the old key is gone from Stripe Dashboard → Developers → API keys after the expiry elapses.

**Rollback**: within the grace window (before expiry), re-setting the old value on Railway and redeploying restores the prior state. After expiry, the old key cannot be reinstated; if the deploy is broken, roll **again** and start over.

### 2.5 Stripe webhook secret

**Effect**: webhook events signed with the old secret will fail HMAC verification and return 401, causing Stripe to retry.

1. Stripe Dashboard → Developers → Webhooks → our endpoint (`https://api.pathforge.eu/api/v1/webhooks/stripe`) → "Reveal" or "Roll" signing secret.
2. On Railway → set `STRIPE_WEBHOOK_SECRET` to the new value → redeploy.
3. In the Stripe Dashboard, trigger a test webhook (`charge.succeeded`) → confirm delivery shows `200` in the webhook logs, not `401`.
4. Monitor for 10 minutes for any `401` webhook deliveries that may indicate Stripe replayed with the old secret (usually Stripe immediately uses the new secret, but pipelining can race).

### 2.6 LLM provider keys

**Effect**: in-flight LLM calls using the old key continue (provider-side session TTL), but all new calls use the new key. No user-visible impact if new key is deployed before the old is revoked.

1. Generate new key in provider dashboard (Anthropic Console / Google AI Studio / Voyage Dashboard).
2. On Railway → update `ANTHROPIC_API_KEY` / `GOOGLE_AI_API_KEY` / `VOYAGE_API_KEY` → redeploy.
3. Monitor the LLM-budget Redis counter for normal cost accrual over the next 10 minutes (`redis-cli GET llm:budget:<YYYY-MM>` or via Langfuse once OPS-3 is live).
4. Revoke the old key at the provider dashboard.

**Rollback**: re-set the old key before revoking it at the provider. Post-revocation there is no rollback.

### 2.7 Email (Resend) API key

**Effect**: verification/password-reset emails fail until new key is live. SPF/DKIM alignment unchanged.

1. Resend Dashboard → API keys → Create new → copy → revoke old (in that order).
2. Railway → `RESEND_API_KEY` → update → redeploy.
3. Smoke test: trigger a password-reset email on a test account.

---

## 3. Incident-driven rotation (suspected compromise)

If a secret may be exposed (leaked in a git commit, captured in a screenshot, in a lost laptop, disclosed by a former contributor):

1. **Revoke first, rotate second.** Go to the provider dashboard and kill the old secret immediately — do not wait to have the new one staged.
2. For JWT: set `JWT_SECRET` and `JWT_REFRESH_SECRET` to temporary random values and redeploy — this signs out every user. Do not try to preserve sessions during an incident.
3. Follow §2 to land the new production value.
4. If git history was the exposure surface: use `git filter-repo` or BFG to purge, then **force-push** main (coordinate with the team — this rewrites history) AND revoke the provider-side secret AND rotate every secret that shared the same git-blob leak.
5. File an incident report: what was exposed, how, when it was first committed, when revoked. Email security@pathforge.eu.

---

## 4. Post-rotation verification

After any rotation, regardless of cause:

- [ ] `curl -sf https://api.pathforge.eu/api/v1/health/ready | jq` → status 200, no probe errors.
- [ ] Synthetic login + refresh → new token works.
- [ ] Synthetic Stripe test charge → webhook delivered 200.
- [ ] Sentry filter for the deploy SHA → no new `ConfigurationError`, no `ValidationError`, no 5xx spike.
- [ ] If DB/Redis password rotated: check connection-pool saturation metric for 10 minutes (brief spike expected, but no sustained backup).
- [ ] Log rotation entry: secret name, rotation time, initiator, reason, old-secret-hash last 4 bytes, verification artefact link.

---

## 5. What NOT to do

- ❌ Never copy a secret into Slack / email / GitHub Issues. Password manager + clipboard only.
- ❌ Never rotate during an active incident that already relies on the secret (e.g. don't rotate DB password while debugging a DB outage).
- ❌ Never rotate `JWT_SECRET` and `JWT_REFRESH_SECRET` to the **same** value — boot guard refuses to start (see [`app/core/config.py :: _validate_jwt_secrets`](../../apps/api/app/core/config.py), Sprint-38 H3).
- ❌ Never set `DATABASE_SSL=false` or `REDIS_SSL=false` in production, even temporarily, to "debug" a TLS handshake error during rotation — boot guard refuses (ADR-0001 / ADR-0002). If TLS is the actual problem, revert the rotation and investigate out-of-band.
- ❌ Never mark a secret as rotated in the calendar without completing §4.

---

## 6. Related

- Ignored CVEs & audit policy: [SECURITY.md](../../SECURITY.md) §"Ignored CVEs"
- Production checklist: [production-checklist.md](production-checklist.md)
- Redis outage runbook: [redis-outage.md](redis-outage.md)
- DB exhaustion runbook: [database-connection-exhaustion.md](database-connection-exhaustion.md)
- ADRs: [ADR-0001 (DB SSL)](../adr/0001-database-ssl-secure-by-default.md), [ADR-0002 (Redis SSL)](../adr/0002-redis-ssl-secure-by-default.md)
