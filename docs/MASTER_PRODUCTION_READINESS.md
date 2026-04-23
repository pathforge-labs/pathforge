# PathForge — Master Production Readiness (SSOT)

> **Status**: Single-source production launch checklist consolidating the prior Tier-1 audit (2026-03-19) and roadmap (2026-02-24) with a fresh `/preflight` full-scan on the current worktree.
> **Generated**: 2026-04-22 · **Branch**: `claude/brave-shaw-16cf72` · **Head**: `9bede13`
> **Prior audits superseded**: `TIER1_PRODUCTION_READINESS_AUDIT.md`, `PRODUCTION_READINESS_ROADMAP.md` (deleted).
> **Stack of record**: Python 3.12 + FastAPI · Next.js 15 · React Native Expo SDK 52 · PostgreSQL 16 + pgvector (Supabase) · Redis · Stripe · Railway + Vercel.

---

## 1. Executive Verdict

| Question | Answer |
| :--- | :--- |
| **Composite Score** | **72.4 / 100** |
| **Verdict** | **CONDITIONAL GO** — code freeze eligible; launch gated on **manual operational setup** (Sprint 40 + Sprint 41 manual tasks). |
| **Code Readiness** | ✅ GO — remediation sprints 39→41 landed. All prior P0 code gaps closed. |
| **Ops Readiness** | ❌ NOT READY — Sentry DSN empty, no Stripe account, no LLM keys, Redis not provisioned, DB SSL off, no uptime monitor. |
| **Blocker Rules** | Zero-Domain: PASS · Security Floor ≥50%: PASS (D5=78) · Quality Floor ≥50%: PASS (D4=82). |
| **Est. remaining effort to GO** | ~1–2 sessions of manual browser/dashboard work across Stripe/Railway/Vercel/UptimeRobot/Sentry + 1 smoke-test session. |

---

## 2. `/preflight` Scorecard (10 Domains)

| # | Domain | Weight | Score | Status | Headline finding |
| :-- | :--- | :--: | :--: | :--- | :--- |
| D1 | Task Tracking & Completion | 10 | 8 | 🟢 | 44 sprints tracked in `docs/ROADMAP.md`; SSOT discipline is strong. Sprint 40/41 manual tasks are the only open blockers. |
| D2 | User Journeys (UX + A11y) | 10 | 7 | 🟡 | 18 dashboard routes + 10 marketing pages + 14 Playwright E2E specs. Axe-core wired. VR baselines still empty. |
| D3 | Implementation (Tests) | 10 | 8 | 🟢 | 1,087+ backend tests, 232+ web tests, 69+ mobile tests, ~28 E2E. No coverage gate in CI yet. |
| D4 | Code Quality | 10 | 8.2 | 🟢 | Ruff/mypy/ESLint/TSC all 0-error; 0 Dependabot vulns after 26-alert sweep. 3 services >24 KB (monitor, not block). |
| D5 | Security | 15 | 11.7 | 🟢 | OAuth JWKS, refresh rotation + replay detect, fail-closed blacklist, 8-layer prompt sanitizer, Stripe webhook HMAC + idempotent dedup. JWT still in localStorage (accepted trade-off). |
| D6 | Configuration / Secrets | 10 | 7 | 🟡 | Production-mode guards block insecure defaults at boot; 100+ settings in one `Settings` class (refactor deferred). No vault; rotation undocumented. |
| D7 | Performance | 10 | 7 | 🟡 | pgvector HNSW, tier-routed LLM, WebP/AVIF, Next.js server components. No N+1 sweep, no response caching on compute-heavy endpoints, no load test. |
| D8 | Documentation | 5 | 4 | 🟢 | 5 incident runbooks + production checklist + architecture/ADRs. README accurate. API docs auto-generated (disabled in prod). |
| D9 | Infrastructure / CI-CD | 10 | 7 | 🟡 | CI green; `pip-audit` + `pnpm audit` now blocking. `deploy.yml` gated by manual `deploy` confirmation. No staging env. |
| D10 | Observability | 10 | 4.5 | 🔴 | Structured logging + Sentry SDK integrated backend+web+mobile, BUT `SENTRY_DSN` empty → **zero prod error visibility**. Langfuse off. No external uptime monitor. |
| | **Total** | **100** | **72.4** | 🟡 | — |

**Blocker Rule Precedence** (evaluated in order, none tripped):

| Rule | Result | Evidence |
| :--- | :--: | :--- |
| Zero-Domain | PASS | lowest domain = D10 @ 4.5/10 (>0) |
| Security Floor (D5 ≥ 50%) | PASS | D5 = 78% |
| Quality Floor (D4 ≥ 50%) | PASS | D4 = 82% |

---

## 3. Remediation State (from prior audit, re-verified)

### 3.1 Code-side P0/P1 — all closed ✅
Evidence walked on current worktree (`9bede13`):

| Prior finding | Status | Evidence |
| :--- | :--: | :--- |
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
| N-2 | No test/CI coverage gate enforced (pytest `--cov` not wired, no threshold). | Medium | Add `--cov=app --cov-fail-under=80` to CI `api-quality` step (planned in Sprint 42). |
| N-3 | `auditConfig.ignoreCves` carries `CVE-2025-69873`, `CVE-2025-09073` without justification comments. | Low | Document rationale + expiry quarter inline or in `SECURITY.md`. |
| N-4 | No staging environment — code goes CI→prod; Vercel previews cover web only. | Medium | Add Railway staging env (Sprint 44 item). |
| N-5 | Langfuse `llm_observability_enabled: false`; LLM cost/latency/quality invisible. | Medium | Activate after OPS-3 so traces are meaningful. |
| N-6 | No load / performance baseline documented for the 12 intelligence endpoints. | Medium | Run `scripts/perf-baseline.sh` once LLM keys live; capture p50/p95 in `docs/baselines/`. |

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

### Gate B — Within 2 sprints post-launch (Sprint 42)
- N-2 Coverage gate ≥80 % on API.
- Welcome email on verification.
- P2-2 `docs/runbooks/secret-rotation.md`.
- P2-3 Circuit-breaker in-memory fallback for Redis outage.
- P2-4 N+1 sweep — enable `warn_on_unnested_lazy_load`; profile top 10 endpoints.
- N-3 / P2-8 Document CVE-ignore justifications.

### Gate C — Live-mode cutover (Sprint 43)
- Stripe live-mode Products + Prices + webhook + signing secret.
- Railway `sk_test_` → `sk_live_`; Vercel `pk_test_` → `pk_live_`.
- First real €19 Pro Monthly transaction; verify payout lands in IBAN.

### Gate D — Post-launch polish (Sprint 44)
- OPS-9 VR baselines committed; `update-baselines.yml` green.
- N-5 Langfuse activation.
- N-4 Railway staging environment.
- N-6 Performance baseline captured.
- Mobile app launch plan.
- Webhook failure alerting in Stripe Dashboard.
- Canary / blue-green deployment evaluation.
- API response caching (5–60 min) on intelligence endpoints.

---

## 5. What's Built (inventory snapshot, 2026-04-22)

### Backend (`apps/api`)
- **32 route files** (`app/api/v1/`), **34 services** (`app/services/`), **22 Alembic migrations**.
- **52 test files**, **1,087+ tests** passing, Ruff ✅ / mypy ✅ (183 files) / pip-audit ✅ (blocking in CI).
- **Security**: OAuth (Google GIS + Microsoft MSAL + JWKS), email verification, password reset w/ independent token column, Turnstile, refresh rotation + replay detect, fail-closed JWT blacklist, 8-layer prompt sanitizer, PII redactor for Langfuse, Stripe webhook HMAC + idempotent dedup + `SELECT FOR UPDATE`, OWASP headers, bot-trap honeypot, prod-mode guards, GDPR export + **full account deletion**.
- **Reliability**: Redis-backed 3-state circuit breaker, LLM $200/month budget guard, RPM limits per tier, ordered graceful shutdown, liveness + deep readiness health checks, connection pool 20+10/pre_ping/recycle 3600s.
- **12 intelligence engines**: Career DNA, Threat Radar, Skill Decay, Salary Intelligence, Career Simulation, Interview Intelligence, Hidden Job Market, Cross-Border Passport, Collective Intelligence, Predictive Career, Recommendation Intelligence, Workflow Automation.

### Web (`apps/web`)
- **Next.js 15 App Router**; marketing (10 pages) + **18 dashboard routes** wired to API: analytics, applications, career-dna, career-passport, career-simulation, command-center, hidden-job-market, interview-prep, matches, notifications, onboarding, recommendations, resumes, salary-intelligence, settings, skill-decay, threat-radar, transition-pathways.
- **14 Playwright E2E specs** (`apps/web/e2e/`) including visual regression + axe-core a11y.
- Sentry (`@sentry/nextjs`) integrated — DSN gated on env.
- Build: 37+ routes, ESLint 0, TSC 0, `pnpm audit` 0 vulns (blocking in CI).

### Mobile (`apps/mobile`)
- Expo SDK 52 + Expo Router; auth flow, API client, resume upload (camera + picker), Career DNA view, push notifications.
- **69 tests** (7 suites).
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
| R1 | Redis outage → rate limit & circuit breaker degrade | Low | High | Fail-closed blacklist done; in-memory circuit-breaker fallback (Sprint 42) pending. |
| R2 | Stripe webhook failure in live mode | Med | High | Sprint 43 verification + webhook alert dashboard. |
| R3 | LLM provider outage | Med | Med | 3-tier fallback chain; monitor via Langfuse once live. |
| R4 | GDPR complaint | Low | Critical | Account deletion shipped + tested. |
| R5 | LLM cost runaway | Low | Med | Redis-backed $200/mo budget guard; add Sentry alert @80 %. |
| R6 | Single Railway instance saturation | Med | Med | Auto-scaling available; surface `RATE_LIMIT_DEGRADED` in `/health/ready` (done). |
| R7 | Stolen refresh token | Low | High | Rotation + replay detect + global invalidation on password change (done). |
| R8 | JWT in localStorage XSS exfiltration | Low | High | CSP + SRI in place; httpOnly cookie migration tracked as P2-1 (post-launch). |
| R9 | No staging env → prod regression | Med | Med | N-4 — add Railway staging (Sprint 44). |

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
