# PathForge — Master Production Readiness (SSOT)

> **Status**: Single-source production launch checklist consolidating the prior Tier-1 audit (2026-03-19) and roadmap (2026-02-24) with a fresh `/preflight` full-scan on the current worktree.
> **Generated**: 2026-04-22 · **Branch**: `main` · **Head**: `0a72ba0` (PR #33 merged 2026-04-26)
> **Prior audits superseded**: `TIER1_PRODUCTION_READINESS_AUDIT.md`, `PRODUCTION_READINESS_ROADMAP.md` (deleted).
> **Stack of record**: Python 3.12 + FastAPI · Next.js 15 · React Native Expo SDK 52 · PostgreSQL 16 + pgvector (Supabase) · Redis · Stripe · Railway + Vercel.
> **Last revision**: 2026-04-27 (Sprint 61) — **Sprint 59-61 follow-on**: closed the residual ADR-0011/-0012 follow-ups identified during the Sprint 55-58 architecture review. **T1-extension** (Sprint 59, PR #38): Sessions tab + Redis-backed `SessionRegistry` with fail-soft pattern + per-session revoke + cookie-CSRF on mutating routes ([ADR-0011](adr/0011-active-session-registry.md)). **§12-decisions** (Sprint 59, PR #39): five Sprint 55-58 open decisions formally accepted as launch policy ([ADR-0012](adr/0012-sprint-55-58-decisions-resolved.md)) — GrowthBook hosting, tier-aware canary scope, causality retention, AI accounting unit, auto-rollback threshold; corresponding settings keys (`causality_retention_days`, `auto_rollback_p0_user_rate_threshold`) codified. **Sprint-60 ratchet** (PR #40): `llm_observability` 85 → 92 % module coverage + styleguide expansion (semantic vs pipeline-execution confidence cap distinction). **Causality purge** (Sprint 61, PR #41): `apps/api/scripts/purge_causality_data.py` with audit-first ordering + new `docs/runbooks/causality-data-retention.md` — operationalises ADR-0012 §#3 GDPR retention. **Round-trip ratchet** (Sprint 61, PR #42): `TransparencyLog` constructor-injectable session factory + 12 SQLite round-trip tests + **latent prod-bug fix**: `entry.timestamp` and `db_record.created_at` were drifting (analysis-time vs. fire-and-forget persist-time) — AI Trust Layer surfaced inconsistent timestamps depending on memory- vs. DB-served path; now a lossless round-trip. **PII hook** (Sprint 61, PR #43): 11 tests cover the entire LiteLLM `input_callback` registrar tree → module 92 → 98 %. **Coverage floor** (Sprint 61, PR #44): `--cov-fail-under` 80 → 85 % in CI, ~10 pp safety headroom against the 94.61 % measurement. Backend test count: **4,331 → 4,461** (+130 across Sprints 59-61). Composite **85.5 → 86.2 (+0.7)** — driven by D3 9.6→9.8 (more tests, higher floor) and D10 7.0→7.5 (causality retention enforced + observability module at 98 %). Two styleguide gaps closed by post-merge Gemini reviews (confidence-cap distinction in PR #40, test-naming patterns in PR #43) — both expansions, not silent drift.

> **Prior revision**: 2026-04-26 (Sprint 58) — Sprint 55-58 six-track work; full text retained in git history (`git show 9747c08:docs/MASTER_PRODUCTION_READINESS.md`).

---

## 1. Executive Verdict

| Question | Answer |
| :--- | :--- |
| **Composite Score** | **86.2 / 100** (↑ 0.7 from Sprint 58 close; arc: 72.4 pre-ADR → 81.7 post-Sprint-44 → 85.5 post-Sprint-58 → **86.2 post-Sprint-61**; **last-measured line coverage 94.61 %** at PR #40 close, with PRs #42-#43 adding 23 net new tests on the 98 %-coverage observability module; **4,461 backend tests**; CI floor lifted to **85 %** in PR #44). Literal sum of the 10 weighted-domain rows in §2. |
| **Verdict** | **CONDITIONAL GO** — code freeze eligible; launch gated on **manual operational setup** only. **Every code-side gap on this document is closed.** |
| **Code Readiness** | ✅ GO — Sprints 39→58 landed + ADR-0001/02 (DB+Redis TLS) + ADR-0006/07/08/09/10 (cookie auth, query budget, AI accounting, canary, webhook DLQ). Prior R8 (JWT-localStorage XSS) closed via T1. P2-4 (N+1 endpoint profiling) closed via T2. N-5 / N-6 closed code-side via T4 / T3. |
| **Ops Readiness** | ❌ NOT READY — Sentry DSN empty, no Stripe account, no LLM keys, Redis not provisioned, no uptime monitor. (DB SSL now auto-enables in prod, no action needed.) |
| **Blocker Rules** | Zero-Domain: PASS · Security Floor ≥50%: PASS (D5=91 %) · Quality Floor ≥50%: PASS (D4=85 %). |
| **Est. remaining effort to GO** | ~1–2 sessions of manual browser/dashboard work across Stripe/Railway/Vercel/UptimeRobot/Sentry + 1 smoke-test session. **No code work remaining for launch.** |

---

## 2. `/preflight` Scorecard (10 Domains)

| # | Domain | Weight | Score | Status | Headline finding |
| :-- | :--- | :--: | :--: | :--- | :--- |
| D1 | Task Tracking & Completion | 10 | 9.0 | 🟢 | 58 sprints tracked in `docs/ROADMAP.md`; SSOT discipline is strong. **Code-side track items 100 % closed.** Manual ops items remain the only open blockers. |
| D2 | User Journeys (UX + A11y) | 10 | 7.5 | 🟡 | 18 dashboard routes + 10 marketing pages + 14 Playwright E2E specs. Axe-core wired. VR h1 timeout root cause fixed. **New `/dashboard/settings/ai-usage` page (T4) ships Transparent AI Accounting** — tier-aware presentation defuses "I don't trust the AI scores" objection. Baselines pending `update-baselines.yml` dispatch. |
| D3 | Implementation (Tests) | 10 | 9.8 | 🟢 | **4,461 backend tests** (+2,709 since Sprint 44; +130 across Sprints 59-61), 267 web, 84 mobile, ~28 E2E. **Last-measured line coverage 94.61 %** at PR #40 close (Sprint 47 target 80 % — far exceeded; CI floor lifted to **85 % in PR #44**, ~10 pp safety headroom). Sessions registry, causality purge, transparency-log round-trip + DI hook (with latent timestamp-drift bug fix), PII redaction-hook coverage to 98 %. Query budget gate still prevents N+1 regressions. |
| D4 | Code Quality | 10 | 8.5 | 🟢 | Ruff/mypy/ESLint/TSC all 0-error; 0 Dependabot vulns. **`@route_query_budget` decorator on every route** (T2) — un-annotated handlers hard-fail in CI. Pii_redactor bug fixed. Mobile lint v9 flat-config migrated (issue #20 closed). |
| D5 | Security | 15 | 13.6 | 🟢 | **JWT now in `httpOnly + Secure + SameSite=Strict` cookies (T1, ADR-0006)** + double-submit CSRF — closes R8 / P2-1 (the localStorage-XSS exfil class). OAuth JWKS, refresh rotation + replay detect, fail-closed blacklist, 8-layer prompt sanitizer, Stripe webhook HMAC. ADR-0001/02 (DB+Redis TLS) intact. **Sentry rollback webhook signature-verified + rate-limited (T5).** |
| D6 | Configuration / Secrets | 10 | 8.8 | 🟢 | Production-mode guards block insecure defaults at boot; ADR-0001/0002 established layered secure-by-default pattern + 7-step ordered validator + CI config-guards job. Secret rotation runbook (11 secrets). 100+ settings in one `Settings` class (refactor deferred). No vault. |
| D7 | Performance | 10 | 8.5 | 🟢 | pgvector HNSW, tier-routed LLM, WebP/AVIF, Next.js server components. Intelligence cache: all 5 dashboard GETs cached. **Pinned p50/p95 baseline for 17 endpoints in `docs/baselines/2026-Q2.json` (T3) + 25 % regression gate in CI** — N-6 closed. **Per-route `@route_query_budget` (T2) prevents N+1 in production**, not just tests. |
| D8 | Documentation | 5 | 5.0 | 🟢 | **14 ADRs** (ADR-0001–0012 + this MPR + sprint-55-58 plan; ADR-0011 active session registry, ADR-0012 §12 decisions resolved both shipped Sprint 59). 8 incident runbooks (added `causality-data-retention.md` Sprint 61) + production checklist + canary-rollback runbook. SECURITY.md §"Ignored CVEs" register. `.gemini/styleguide.md` expanded twice this session (confidence-cap distinction PR #40, test-naming patterns PR #43) — both close real gaps surfaced by post-merge Gemini reviews. README accurate. API docs auto-generated (disabled in prod). |
| D9 | Infrastructure / CI-CD | 10 | 8.0 | 🟢 | CI green; `pip-audit` + `pnpm audit` blocking; coverage gate at floor. `deploy.yml` gated by manual confirmation. `deploy-staging.yml` ready. **GrowthBook-style flag system + Sentry-triggered auto-rollback (T5, ADR-0009)** supersedes ADR-0005 PARK; tier-aware canary delays paying-tier exposure on major releases by 24 h. Staging activation pending 5 manual Railway steps (N-4). |
| D10 | Observability | 10 | 7.5 | 🟢 | Structured logging + Sentry SDK integrated. `/health/ready` exposes structured `db` + `redis_detail` with TLS attestation. **Langfuse activated (T4, ADR-0008)** — per-engine trace + cost telemetry; `/dashboard/settings/ai-usage` exposes the data to users. **Webhook DLQ ledger (T6, ADR-0010)** — `webhook_event` table + admin replay surface; 15-min scheduled production smoke. **AI Trust Layer™ round-trip integrity** (Sprint 61, PR #42) — fixed latent `entry.timestamp` ↔ `db.created_at` drift so memory- and DB-served records report the same instant. **Causality data retention enforced** (Sprint 61, PR #41 + ADR-0012 §#3) — daily cron purge with audit-first ordering protects the GDPR contract while preserving anonymised aggregates forever via `logs/causality_purge_aggregates.jsonl`. **PII redaction hook** at 98 % coverage including the deep-copy-before-redact invariant (Sprint 39 audit A-H3). `SENTRY_DSN` still empty (OPS-1) → no prod error visibility until manual setup. No external uptime monitor (OPS-6). |
| | **Total** | **100** | **86.2** | 🟢 | Literal sum of weighted-domain scores above. Arc: 72.4 → 75.0 (ADR-0001) → 76.9 (ADR-0002) → 77.4 (docs) → 78.2 (P2-3/N-7) → 79.1 (cache+R5) → 79.9 → 80.3 → 80.5 → 81.1 → 81.7 (Sprint 44 close) → 85.5 (Sprint 58 close: T1-T6 shipped, ADR-0006/07/08/09/10, 4,331 tests, 94.36 %) → **86.2 (Sprint 61 close: ADR-0011/-0012 follow-ons + observability ratchet + coverage floor 80 → 85 %; 4,461 tests, 94.61 %+, PRs #38-#44)**. The +0.7 delta from 85.5 captures D3 9.6→9.8 and D10 7.0→7.5. |

**Blocker Rule Precedence** (evaluated in order, none tripped):

| Rule | Result | Evidence |
| :--- | :--: | :--- |
| Zero-Domain | PASS | lowest domain = D10 @ 7.0/10 (>0; was 5.3 pre-Sprint-58) |
| Security Floor (D5 ≥ 50%) | PASS | D5 = 91 % |
| Quality Floor (D4 ≥ 50%) | PASS | D4 = 85 % |

---

## 3. Remediation State (from prior audit, re-verified)

### 3.1 Code-side P0/P1 — all closed ✅
Evidence walked on current worktree (`5067554`, post-PR #3 merge):

| Prior finding | Status | Evidence |
| :--- | :--: | :--- |
| N-1 Database SSL secure-by-default | ✅ Done | [ADR-0001](adr/0001-database-ssl-secure-by-default.md) · PR #2 (2026-04-23). Auto-derives in production, fails boot on explicit downgrade, Alembic shares TLS context, readiness attests server-side cipher, Sentry tags every event. 46 new tests. Also closes **OPS-5**. |
| N-1b Redis SSL secure-by-default | ✅ Done | [ADR-0002](adr/0002-redis-ssl-secure-by-default.md) · PR #3 (2026-04-23). Parallel Redis TLS hardening; consolidates 5 call sites (token blacklist, rate limiter, ARQ worker, LLM budget guard, circuit breaker) onto shared helper; upgrade-only scheme reconciliation; ARQ `ssl_check_hostname=True` closes MITM vector; `ConfigurationError(RuntimeError)` prevents DSN leak via Pydantic `ValidationError`; **closes latent plaintext bug** in `app/core/llm.py:112` (LLM budget guard was ignoring `redis_ssl`). 70 new tests. |
| P0-1 GDPR full account deletion | ✅ Done | `apps/api/app/services/account_deletion_service.py`, `apps/api/tests/test_account_deletion.py` (5 tests), `DELETE /api/v1/users/me` wired. |
| P0-2 Sentry SDK integrated | ✅ Code / ❌ Activation | `sentry.client.config.ts`, `sentry.server.config.ts`, `sentry.edge.config.ts`, `apps/api/app/core/sentry.py`. DSN empty. |
| P0-7 Pricing SSOT | ✅ Done | Sprint 39. |
| P0-8 OAuth social login | ✅ Done | `apps/api/app/api/v1/oauth.py`, Google GIS + Microsoft MSAL + JWKS. |
| P1-1 Token blacklist fail mode | ✅ Done | `security.py:116-134` — configurable `TOKEN_BLACKLIST_FAIL_MODE` (default closed). |
| P1-2 Refresh token rotation | ✅ Done | Commit `d7473ce` — atomic refresh rotation, replay detect, global invalidation, rate-limited logout. |
| P1-3 CI security scans blocking | ✅ Done | `.github/workflows/ci.yml` — `continue-on-error` removed from `pip-audit` + `pnpm audit`. |
| P1-4 Health check degradation surface | ✅ Done | `/health/ready` returns 503 when rate limiter in `memory://` mode. |
| P1-6 Incident runbooks | ✅ Done | 5 runbooks under `docs/runbooks/` (Redis, DB exhaustion, Stripe webhook, LLM budget, DDoS) + migration-safety + production-checklist. |
| P2 token separation (reset vs. verify) | ✅ Done | Migration `e5f6g7h8i9j0`; `password_reset_token` + `password_reset_sent_at` independent from verification token. |

### 3.2 Operational gaps — **open**
Code is ready, but these require a human in the Stripe/Railway/Vercel/UptimeRobot/Sentry consoles:

| # | Gap | Surface | Files / where |
| :-- | :--- | :--- | :--- |
| **OPS-1** | **Sentry DSN empty** | Railway + Vercel env | `SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_DSN` |
| **OPS-2** | **Stripe account not provisioned** | Stripe Dashboard + Railway + Vercel env | KVK, IBAN, 4 Products, webhook endpoint `https://api.pathforge.eu/api/v1/webhooks/stripe`, 6 events; `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, 4× `STRIPE_PRICE_ID_*`, `BILLING_ENABLED=true`, `NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY`. |
| **OPS-3** | **LLM API keys absent** | Railway env | `ANTHROPIC_API_KEY`, `GOOGLE_AI_API_KEY`, `VOYAGE_API_KEY`, `LLM_MONTHLY_BUDGET_USD=200`. |
| **OPS-4** | **Redis not provisioned in prod** | Railway plugin or Upstash | `REDIS_URL`, `RATELIMIT_STORAGE_URI=redis://…`. Without it: rate limit degrades to per-instance memory, circuit breaker loses state, LLM budget guard can't cap. |
| ~~**OPS-5**~~ | ~~`DATABASE_SSL=false`~~ — **closed by ADR-0001 (2026-04-23)**. TLS auto-enables when `ENVIRONMENT=production`; explicit `false` in prod now fails boot. Verify post-deploy via `curl /api/v1/health/ready \| jq .db.ssl`. | — | — |
| **OPS-6** | **No uptime monitor** | UptimeRobot (free tier) | `https://api.pathforge.eu/api/v1/health/ready` + `https://pathforge.eu`, 5-min poll, alert → `emre@pathforge.eu`. |
| **OPS-7** | **Full env-var audit not run** | Railway + Vercel | Verify `ENVIRONMENT`, `JWT_SECRET`, `JWT_REFRESH_SECRET`, `DATABASE_URL`, `CORS_ORIGINS`, `INITIAL_ADMIN_EMAIL`, `NEXT_PUBLIC_API_URL`. |
| **OPS-8** | **`alembic current` on prod unverified** | Railway shell | `alembic current` → `alembic upgrade head` if behind. |
| **OPS-9** | **VR baselines empty** | `apps/web/e2e/__screenshots__/` | Run `update-baselines.yml` once Sentry/LLM are live; commit. |

### 3.3 New findings this scan

| # | Finding | Severity | Action |
| :-- | :--- | :-- | :--- |
| ~~N-1~~ | ~~`database_ssl` default is `False`~~ — **closed 2026-04-23 via [ADR-0001](adr/0001-database-ssl-secure-by-default.md)**. Auto-derives from `ENVIRONMENT`; explicit `false` in prod fails boot; Alembic + runtime use the same hardened TLS context; readiness probe attests server-side `ssl_cipher`. | — | — |
| ~~N-2~~ | ~~Coverage floor at 65% (Sprint 42 baseline lock).~~ — **closed 2026-04-23 (Sprint 44)**. `--cov-branch` enabled; floor 62% (line+branch, conservative: 1% above pre-Sprint-43 combined baseline; Sprint 43 added ~55 new tests). Ratchet: Sprint 45 → 70%; Sprint 46 → 75%; Sprint 47 → 80%. Gate B N-2 item ✅ in progress. | — | — |
| ~~N-3~~ | ~~`auditConfig.ignoreCves` carries `CVE-2025-69873`, `CVE-2025-09073` without justification comments.~~ — **closed 2026-04-23** via P2-8. Justification register added to [SECURITY.md](../SECURITY.md) §"Ignored CVEs" (dev-only ESLint/ajv false positives, re-evaluate 2026-Q4). `package.json` `auditConfig` carries a `__justifications` pointer to the register. | — | — |
| N-4 | No staging environment — code goes CI→prod; Vercel previews cover web only. | Medium | Add Railway staging env. `deploy-staging.yml` + runbook ready Sprint 44; activation pending 5 manual Railway steps. |
| ~~N-5~~ | ~~Langfuse `llm_observability_enabled: false`; LLM cost/latency/quality invisible.~~ — **closed code-side 2026-04-26 (Sprint 56, T4, [ADR-0008](adr/0008-transparent-ai-accounting.md))**. Langfuse SDK wired with sampling + PII redaction; per-engine cost telemetry surfaced to users at `/dashboard/settings/ai-usage` (tier-aware presentation: scans for free, EUR for premium). Trace volume controlled per-user. Awaiting OPS-3 LLM keys before traces become meaningful in prod. | — | — |
| ~~N-6~~ | ~~No load / performance baseline documented for the 12 intelligence endpoints.~~ — **closed 2026-04-26 (Sprint 56, T3)**. Pinned `docs/baselines/2026-Q2.json` covers 17 endpoints (health + intelligence dashboards + auth); CI `perf-baseline-regression` job fails any PR with > 25 % p95 drift. Refresh policy in `docs/baselines/README.md`. | — | — |
| ~~N-7~~ | ~~Deprecated transitive packages in `pnpm-lock.yaml` had no explicit triage decision, blocking future `package.json` touches.~~ — **closed 2026-04-23** (Sprint 43). Five deprecated packages triaged in [docs/dep-triage.md](dep-triage.md). All are dev-only, no CVE, blocked on upstream parent upgrades — PARK decision justified for each. | — | — |

---

## 4. Launch Blockers — Ordered Remediation Plan

### Gate A — Must complete before `/deploy` (hard blockers)
Estimated ≤1 working session (mostly clicks in external dashboards).

1. **OPS-2** Provision Stripe test mode → webhook → set 7 Railway env vars + 1 Vercel env var → test with `4242 4242 4242 4242`.
2. **OPS-3** Create Anthropic + Google AI + Voyage AI keys → set in Railway → `LLM_MONTHLY_BUDGET_USD=200`.
3. **OPS-4** Provision Redis (Railway plugin or Upstash free) → set `REDIS_URL` + `RATELIMIT_STORAGE_URI`.
4. ~~**OPS-5 / N-1**~~ — closed by [ADR-0001](adr/0001-database-ssl-secure-by-default.md); no manual step required. Verify post-deploy that `curl /api/v1/health/ready` returns `db.ssl: true`.
5. **OPS-1** Create Sentry project → set `SENTRY_DSN` + `NEXT_PUBLIC_SENTRY_DSN` → fire synthetic 500 to verify PII-scrubbed event lands.
6. **OPS-7** Walk the full env-var checklist in `docs/runbooks/production-checklist.md`.
7. **OPS-8** `alembic current` on prod → `alembic upgrade head` if behind.
8. **OPS-6** UptimeRobot monitors on `/api/v1/health/ready` and `https://pathforge.eu`, 5-min, email → `emre@pathforge.eu`.
9. **Smoke test** (end-to-end, prod env): Register → Verify email → Login → Upload CV → Career DNA → Checkout → Subscription → Customer portal → **Delete account** → re-register with same email.

Pass criteria: every Gate A step produces observable evidence (Sentry event ID, Stripe charge ID, UptimeRobot monitor ID, `curl /health/ready` 200, successful round-trip smoke).

### Gate B — Within 2 sprints post-launch (Sprint 42–43)
- ~~N-2 Coverage gate ≥80% on API.~~ ✅ closed Sprint 47; **94.36 % line coverage as of Sprint 58** (target was 80 %).
- ~~Welcome email on verification.~~ ✅ confirmed implemented (Sprint 42 audit).
- ~~P2-2 `docs/runbooks/secret-rotation.md`.~~ ✅ closed 2026-04-23.
- ~~P2-3 Circuit-breaker adopted — [ADR-0003](adr/0003-circuit-breaker-adopted-for-external-apis.md) + wired into Adzuna, Jooble, Voyage AI.~~ ✅ closed 2026-04-23.
- ~~P2-4 N+1 sweep / endpoint profiling.~~ ✅ closed Sprint 55 (T2). `@route_query_budget(max_queries=N)` decorator on every router-mounted handler in `app/api/v1/`; autouse fixture hard-fails any PR exceeding declared budget; un-annotated handlers also hard-fail.
- ~~P2-1 / R8 JWT in localStorage XSS exfiltration~~ ✅ closed Sprint 55 (T1, [ADR-0006](adr/0006-auth-via-httponly-cookies.md)). JWT moved to `httpOnly + Secure + SameSite=Strict` cookies + double-submit CSRF. 30-day legacy-bearer overlap window for in-flight clients.
- ~~N-3 / P2-8 Document CVE-ignore justifications.~~ ✅ closed 2026-04-23.
- ~~N-7 Dep triage — [docs/dep-triage.md](dep-triage.md) documents all deprecated transitives.~~ ✅ closed 2026-04-23.

### Gate C — Live-mode cutover (Sprint 43)
- Stripe live-mode Products + Prices + webhook + signing secret.
- Railway `sk_test_` → `sk_live_`; Vercel `pk_test_` → `pk_live_`.
- First real €19 Pro Monthly transaction; verify payout lands in IBAN.

### Gate D — Post-launch polish (Sprint 44)
- OPS-9 VR baselines committed; `update-baselines.yml` green.
- ~~N-5 Langfuse activation.~~ ✅ closed code-side Sprint 56 (T4, [ADR-0008](adr/0008-transparent-ai-accounting.md)). Awaits OPS-3 LLM keys for live traces.
- N-4 Railway staging environment — `deploy-staging.yml` + runbook ready; pending 5 manual Railway steps.
- ~~N-6 Performance baseline captured.~~ ✅ closed Sprint 56 (T3) — `docs/baselines/2026-Q2.json` + CI regression gate.
- ~~Mobile app launch plan.~~ ✅ closed Sprint 44 (`docs/mobile-launch-plan.md` 6-phase).
- ~~Webhook failure alerting~~ ✅ closed Sprint 58 (T6, [ADR-0010](adr/0010-webhook-dlq-and-prod-smoke.md)) — `webhook_event` ledger + admin replay surface + 15-min scheduled prod smoke.
- ~~Canary / blue-green deployment evaluation.~~ ✅ closed Sprint 57 (T5, [ADR-0009](adr/0009-progressive-deployment-canary.md)) supersedes ADR-0005. GrowthBook-style flag + Sentry-triggered auto-rollback + tier-aware canary delay (paying users trail major releases by 24 h).
- ~~API response caching (5–60 min) on intelligence endpoints.~~ ✅ closed Sprint 43–44: all 5 intelligence dashboard GETs cached via `ic_cache` (15–60 min TTL, fail-open).

---

## 5. What's Built (inventory snapshot, 2026-04-27)

### Backend (`apps/api`)
- **35+ route files** (`app/api/v1/` + `admin_webhooks` + `ai_usage` + `sentry_auto_rollback` + `sessions`), **35+ services**, **22+ Alembic migrations**, **1 maintenance script** (`apps/api/scripts/purge_causality_data.py` — daily-cron causality retention).
- **170+ test files**, **4,461 tests** passing (last-measured line coverage **94.61 %** at PR #40 close — 15,937 / 16,889 statements; CI `--cov-fail-under` lifted to **85 %** in PR #44); Ruff ✅ / mypy ✅ / pip-audit ✅ (blocking in CI).
- **Auth**: JWT in `httpOnly + Secure + SameSite=Strict` cookies (T1, ADR-0006) + double-submit CSRF + 30-day bearer-header overlap; OAuth (Google GIS + Microsoft MSAL + JWKS); email verification; password reset; Turnstile; refresh rotation + replay detect; fail-closed JWT blacklist. **Active-session registry** (T1-extension, [ADR-0011](adr/0011-active-session-registry.md)): Redis-backed `SessionRegistry` (`session:user:{id}` SET + `session:meta:{jti}` HASH) with fail-soft pattern + UA→device-label heuristic; `/api/v1/sessions` + DELETE + revoke-others endpoints; cookie-CSRF on all mutating routes.
- **Security**: 8-layer prompt sanitizer, PII redactor for Langfuse, Stripe webhook HMAC + idempotent dedup + `SELECT FOR UPDATE`, OWASP headers, bot-trap honeypot, prod-mode guards, GDPR export + **full account deletion**.
- **Reliability**: Redis-backed 3-state circuit breaker, LLM $200/month budget guard + Sentry @80 % alert, RPM limits per tier, ordered graceful shutdown, liveness + deep readiness health checks, connection pool 20+10/pre_ping/recycle 3600s. **`@route_query_budget` per route + autouse hard-fail gate (T2)**.
- **Observability**: Structured logging + Sentry SDK; **Langfuse trace shipping wired (T4)**; `/health/ready` exposes structured `db` + `redis_detail` with TLS attestation; **pinned p50/p95 baseline for 17 endpoints (T3)** + 25 % regression gate.
- **Deployment safety**: GrowthBook-style flag system + tier-aware canary + Sentry-triggered auto-rollback (T5, ADR-0009).
- **Webhook resilience**: `webhook_event` DLQ ledger + admin replay surface + 15-min scheduled prod smoke (T6, ADR-0010).
- **12 intelligence engines**: Career DNA, Threat Radar, Skill Decay, Salary Intelligence, Career Simulation, Interview Intelligence, Hidden Job Market, Cross-Border Passport, Collective Intelligence, Predictive Career, Recommendation Intelligence, Workflow Automation.

### Web (`apps/web`)
- **Next.js 15 App Router**; marketing (10 pages) + **19 dashboard routes** wired to API (added `/dashboard/settings/ai-usage` for Transparent AI Accounting in T4); cookie-first auth via `credentials: "include"` + `X-CSRF-Token` (T1).
- **14 Playwright E2E specs** (`apps/web/e2e/`) including visual regression + axe-core a11y.
- **267 vitest unit tests** (was 232 pre-Sprint-58); SSR-safe feature flag SDK (T5); SSR-safe relative-time hook on AI usage page.
- Sentry (`@sentry/nextjs`) integrated — DSN gated on env.
- Build: 38+ routes, ESLint 0, TSC 0, `pnpm audit` 0 vulns (blocking in CI).

### Mobile (`apps/mobile`)
- Expo SDK 52 + Expo Router; auth flow (uses `expo-secure-store`, never localStorage), API client, resume upload (camera + picker), Career DNA view, push notifications.
- **84 tests** (8 suites).
- **ESLint v9 flat-config migrated** (issue #20 closed Sprint 54).
- Sentry (`@sentry/react-native`) integrated.

### Infra
- **Railway** API (manual `deploy.yml` with pre-flight validation + post-deploy health check + rollback).
- **Vercel** web (monorepo config, auto-deploy disabled, previews on PR).
- Resend email (SPF/DKIM/DMARC verified).
- GA4 + Consent Mode v2.
- `pathforge.eu` DNS live.

---

## 6. Open Risks Register

| # | Risk | Likelihood | Impact | Mitigation |
| :-- | :--- | :--: | :--: | :--- |
| R1 | Redis outage → rate limit & circuit breaker degrade | Low | High | ~~in-memory circuit-breaker fallback pending~~ ✅ closed Sprint 43: `fail_open=True` on CircuitBreaker — Redis unavailable → CLOSED state assumed, calls proceed. Rate limiter degrades to per-instance memory (surfaced in `/health/ready`). |
| R2 | Stripe webhook failure in live mode | Med | High | ~~Sprint 43 verification + webhook alert dashboard.~~ ✅ closed Sprint 58 (T6, [ADR-0010](adr/0010-webhook-dlq-and-prod-smoke.md)) — `webhook_event` ledger + admin replay surface + 15-min scheduled prod smoke. |
| R3 | LLM provider outage | Med | Med | 3-tier fallback chain; ✅ Langfuse trace shipping wired (T4); awaits OPS-3 keys to be meaningful in prod. |
| R4 | GDPR complaint | Low | Critical | Account deletion shipped + tested. |
| R5 | LLM cost runaway | Low | Med | ~~add Sentry alert @80%~~ ✅ closed Sprint 43: `_check_budget()` fires `sentry_sdk.capture_message` once per month when spend ≥ 80% (Redis-deduped). Budget guard unchanged. **User-facing AI accounting (T4) lets users self-monitor.** |
| R6 | Single Railway instance saturation | Med | Med | Auto-scaling available; surface `RATE_LIMIT_DEGRADED` in `/health/ready` (done). **Per-route query budget (T2) prevents accidental N+1 surge under load.** |
| R7 | Stolen refresh token | Low | High | Rotation + replay detect + global invalidation on password change (done). **httpOnly cookie storage (T1) closes the access-token side too.** |
| ~~R8~~ | ~~JWT in localStorage XSS exfiltration~~ ✅ **closed Sprint 55 (T1, [ADR-0006](adr/0006-auth-via-httponly-cookies.md))** — JWT moved to `httpOnly + Secure + SameSite=Strict` cookies; XSS can no longer read the auth token via JS. Double-submit CSRF protects mutating routes. 30-day bearer-header overlap window for in-flight clients. | — | — | — |
| R9 | No staging env → prod regression | Med | Low | N-4 — `deploy-staging.yml` + runbook ready Sprint 44; pending 5 manual Railway steps. **Canary + auto-rollback (T5) reduces impact even on a direct-to-prod regression.** |

---

## 7. Verification Checklist (post-Gate A smoke)

- [ ] `curl https://api.pathforge.eu/api/v1/health/ready` → 200 with DB+Redis+rate-limit all OK.
- [ ] Synthetic 500 → Sentry event visible with PII scrubbed.
- [ ] CI fails on a branch introducing a known vulnerable dep.
- [ ] `/health/ready` returns 503 when Redis is stopped.
- [ ] UptimeRobot alert fires within 5 min of API stop.
- [ ] Refresh rotation: reused refresh token → 401.
- [ ] `DELETE /api/v1/users/me` cascades across all user-linked tables, revokes tokens, cancels Stripe sub.
- [ ] Full journey smoke: register → verify → login → upload CV → Career DNA → checkout (test card) → subscription active → customer portal → delete account → same-email re-register succeeds.

---

## 8. Governance

- **SSOT** for sprint-level tasks: `docs/ROADMAP.md`.
- **SSOT** for production-launch readiness: this document.
- **Preflight re-run cadence**: after every `feat`, `fix`, `refactor`, `perf` commit; `/preflight --rescan` for delta.
- **Launch gate owner**: `emre@pathforge.eu`.
- **Required approvals before live-mode flip**: Gate A smoke checklist complete + human Go/No-Go.

---

*Consolidates `TIER1_PRODUCTION_READINESS_AUDIT.md` (2026-03-19) and `PRODUCTION_READINESS_ROADMAP.md` (2026-02-24). Both archived-by-deletion in the commit that introduced this file.*
