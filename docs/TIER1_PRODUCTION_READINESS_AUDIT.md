# PathForge — Tier-1 Production Readiness Audit Report

> **Auditor**: Senior Staff Engineer (Autonomous Authority)
> **Date**: 2026-03-19
> **Commit**: `8e6425c`
> **Prior Audit**: Sprint 38 — "Code quality GO, Operational readiness NO-GO" (8 P0, score 49/100)
> **Scope**: Full codebase audit after Sprint 39 auth hardening remediation

---

## 0. TECH STACK CORRECTION

The initial audit brief referenced Flutter/Riverpod 3, NestJS, Strangler Fig migration, Typesense→Elasticsearch, Mollie Connect, iDIN, and PostNL/DHL logistics. **None of these exist in this codebase.** All audit domains below are assessed against the actual architecture:

| Layer | Actual Technology | Brief Assumption |
|---|---|---|
| Backend | Python FastAPI 3.12+ | NestJS modular monolith |
| Web Frontend | Next.js 15 (App Router) | Flutter/Riverpod 3 |
| Mobile | React Native + Expo SDK 52 | Flutter/Riverpod 3 |
| Database | PostgreSQL 16 + pgvector (Supabase) | Supabase→NestJS Strangler Fig |
| Payments | Stripe SDK (test mode) | Mollie Connect |
| Identity | Email verification + OAuth (Google/Microsoft) | iDIN identity verification |
| Search | pgvector HNSW semantic similarity | Typesense→Elasticsearch |
| Logistics | N/A | PostNL/DHL |

---

## 1. EXECUTIVE SUMMARY

### Verdict: **CONDITIONAL GO** — Launch-ready after Sprint 41

**Rationale**: Sprint 39 resolved the critical auth lifecycle blockers (6/8 Sprint 38 P0s). The codebase demonstrates production-grade engineering: defense-in-depth security, circuit breakers, structured logging, comprehensive error handling, and 1,087+ tests across backend, web, and mobile. The remaining blockers are **operational activation** (Stripe account, LLM keys, Sentry DSN, DB SSL, Redis production) — all scheduled in Sprints 40–41.

One **new P0** identified this audit: GDPR full account deletion endpoint is missing and not scheduled in any sprint.

### Top 3 Risks to Production Stability

1. **Sentry not active in production** — errors currently go undetected. No observability until Sprint 41 activation.
2. **Token blacklist degrades open on Redis failure** — revoked tokens accepted during Redis outage (`security.py:124`).
3. **No full account deletion** — GDPR Article 17 non-compliance for Dutch users with real PII.

### Readiness Scores (0–100)

| Domain | Sprint 38 | Current (Sprint 39+) | Target (Post–Sprint 41) |
|---|---|---|---|
| Security | 55 | 78 | 85 |
| Reliability | 60 | 75 | 80 |
| Observability | 20 | 45 | 70 |
| Performance | 65 | 70 | 75 |
| CI/CD & Deployment | 60 | 72 | 80 |
| Compliance | 40 | 65 | 80 |
| **Composite** | **49** | **68** | **78** |

### Go/No-Go Decision Matrix

- **GO** requires: all domains ≥60, zero open P0s
- **CONDITIONAL GO** requires: all domains ≥40, P0s have scheduled sprints
- **NO-GO**: any domain below 40 or ≥3 unscheduled P0s

**Current**: CONDITIONAL GO — Observability at 45 (above 40 threshold), 1 new P0 needs scheduling.

---

## 2. DOMAIN FINDINGS

### 2.1 Architecture Integrity

**Assessment: STRONG (78/100)**

The monorepo is well-structured with clean module boundaries and correct dependency direction.

| Priority | Area | Finding | Remediation |
|---|---|---|---|
| [POSITIVE] | Module Boundaries | 32 route modules, 32 services, 32 models — consistent 1:1:1 pairing. No circular imports. `main.py` registers 30 routers with clear prefix conventions. | — |
| [POSITIVE] | Lifespan Management | Ordered startup (logging→observability→Sentry→Stripe pin→admin promotion) and shutdown (Sentry flush→Redis→DB→HTTP client). Duration measured. | — |
| [P3] | Service Sizes | `billing_service.py` (26KB), `recommendation_intelligence_service.py` (28KB), `career_dna_service.py` (24KB) approaching complexity threshold. Cohesive but large. | Monitor; extract domain sub-services if they grow further. |
| [P3] | Config Sprawl | 100+ settings in single `Settings` class (`config.py`). Currently manageable. | Consider domain-specific config objects (e.g., `LLMConfig`, `BillingConfig`) in future refactor. |

### 2.2 Security Posture

**Assessment: GOOD (78/100) — Major improvement from Sprint 38 (55)**

Sprint 39 delivered comprehensive auth hardening. Critical gaps remain in GDPR compliance and token lifecycle.

| Priority | Area | Finding | Remediation |
|---|---|---|---|
| **[P0]** | **GDPR Art. 17** | **No full account deletion endpoint.** Career DNA deletion exists (`DELETE /career-dna`), GDPR data export exists (`POST /user-profile/exports`), but no endpoint to delete entire user account across 32 models. Dutch users with real PII require this. **Not scheduled in any sprint.** | Add `DELETE /api/v1/users/me` — cascade deletion across all user-linked models, revoke tokens, cancel Stripe subscription, create audit trail. Files: `user_profile.py`, `user_profile_service.py`. |
| [P1] | Token Blacklist | Degrades **open** on Redis failure. `security.py:112-124` — catch-all at L123 logs warning, allows request. Revoked tokens (e.g., compromised account forced-logout) accepted during Redis outage. | Add configurable `TOKEN_BLACKLIST_FAIL_MODE` (closed/open). Default to closed for security-critical deployments. |
| [P1] | Refresh Token Rotation | Not implemented. Stolen refresh token grants 30-day access without detection. Planned Sprint 42. | Elevate to Sprint 41. On each refresh, issue new refresh token + revoke old one. |
| [P1] | CI Security Scans | `pip-audit` (`ci.yml:104`) and `pnpm audit` (`ci.yml:148`) both `continue-on-error: true`. Known CVEs can ship to production. Planned Sprint 44. | Elevate to Sprint 41. Remove `continue-on-error: true`. |
| [P2] | Token Storage | localStorage for JWT in `token-manager.ts`. XSS vulnerability would expose both tokens. Mitigated by CSP but inherent risk. | Move refresh token to httpOnly cookie; access token in memory only. |
| [P2] | Secret Rotation | No mechanism for rotating JWT secrets, Stripe keys, or LLM API keys. Manual rotation requires restart. | Document rotation procedure in runbook. Consider admin endpoint for phased JWT rotation. |
| [P2] | Ignored CVEs | `auditConfig.ignoreCves` contains `CVE-2025-69873`, `CVE-2025-09073`. | Review quarterly; document justification for each ignore. |
| [POSITIVE] | Auth Lifecycle | Sprint 39: email verification (SHA-256 tokens), password reset (enumeration-safe), OAuth (Google + Microsoft JWKS), Turnstile CAPTCHA, password complexity. | — |
| [POSITIVE] | Prompt Injection | 8-layer sanitizer: instruction overrides, role markers, chat templates, delimiter injection, zero-width chars, Unicode normalization, whitespace, length. | — |
| [POSITIVE] | Webhook Security | Stripe signature verification, idempotent dedup, timestamp ordering, `SELECT FOR UPDATE`, fast-ack pattern. | — |
| [POSITIVE] | OWASP Headers | X-Content-Type-Options, X-Frame-Options: DENY, HSTS 1yr+preload, Referrer-Policy, Permissions-Policy, Cache-Control no-store. Bot trap honeypot. | — |
| [POSITIVE] | Production Guards | JWT secret validator blocks startup with insecure defaults. Docs/redoc/openapi disabled in production. CORS restricted to `pathforge.eu`. | — |

### 2.3 Reliability Engineering

**Assessment: GOOD (75/100)**

Defense-in-depth resilience with circuit breakers, budget guards, and graceful shutdown. Redis dependency is the common failure mode.

| Priority | Area | Finding | Remediation |
|---|---|---|---|
| [P1] | Rate Limit Degradation | Memory fallback (`memory://`) when Redis unavailable breaks multi-instance rate limiting. `RATE_LIMIT_DEGRADED` flag not surfaced in health check. | Surface in `/health/ready` response. Consider failing readiness probe when degraded. |
| [P2] | Circuit Breaker Redis | Circuit breaker stores state in Redis. Redis outage means circuit breaker can't track failures — falls back to allowing all requests. | Add in-memory fallback for circuit breaker state (per-instance accuracy > no circuit breaking). |
| [P2] | Database SSL | `database_ssl: bool = False` by default (`config.py:56`). Production Supabase connection unencrypted. Sprint 41 planned. | Set `DATABASE_SSL=true` in Railway env vars. |
| [POSITIVE] | Circuit Breaker | Redis-backed 3-state machine (CLOSED→OPEN→HALF_OPEN). Configurable threshold (3 failures), recovery (300s), auto-expire (1h). Applied to Adzuna, Jooble, Voyage AI. | — |
| [POSITIVE] | LLM Budget Guard | $200/month Redis-backed cap with `INCRBYFLOAT`. RPM limits: Primary 60, Fast 200, Deep 10. 3-tier fallback chain. Retry with exponential backoff (1s, 2s, 4s). | — |
| [POSITIVE] | Graceful Shutdown | Ordered: Sentry flush(2s)→Redis close→DB dispose→HTTP client close. Duration logged. | — |
| [POSITIVE] | Health Checks | Liveness + deep readiness (DB + Redis + rate limit). 503 on dependency failure. Cold start tracking. Used by Railway health check. | — |
| [POSITIVE] | Connection Pool | size=20, max_overflow=10, pre_ping=True, recycle=3600s, timeout=30s. Appropriate for expected load. | — |

### 2.4 Performance Optimization

**Assessment: ADEQUATE (70/100)**

Fundamentals in place. No systematic performance analysis has been done for production load.

| Priority | Area | Finding | Remediation |
|---|---|---|---|
| [P2] | N+1 Queries | Only `User.subscription` uses `selectinload` (`security.py:128`). 32 models with relationships — other services may have unguarded lazy loads across 156 endpoints. | Enable `warn_on_unnested_lazy_load` in dev. Profile top 10 most-called endpoints. |
| [P3] | API Caching | All responses use `Cache-Control: no-store`. Intelligence endpoints (Career DNA, Threat Radar, Salary) are compute-heavy but change infrequently. | Add short-lived caching (5-60 min) for read-heavy intelligence endpoints. |
| [POSITIVE] | pgvector Search | HNSW index for sub-100ms semantic similarity on job listing embeddings. | — |
| [POSITIVE] | LLM Tier Routing | 80/15/5 split across Primary/Fast/Deep. Cost-optimized for workload type. Budget guard prevents runaway. | — |
| [POSITIVE] | Web Optimization | WebP conversion (Sprint 6a.1), Next.js App Router server components, AVIF preference in next.config. | — |

### 2.5 Operational Readiness

**Assessment: NEEDS WORK (45/100) — Primary blocker for GO verdict**

Code is instrumented but nothing is active in production yet. This is the domain that needs Sprint 41 to unlock.

| Priority | Area | Finding | Remediation |
|---|---|---|---|
| **[P0]** | **Sentry Inactive** | **Sentry SDK integrated (backend + web + mobile) but DSN empty.** Zero error visibility in production. Sprint 41 planned. | Set `SENTRY_DSN` in Railway + `NEXT_PUBLIC_SENTRY_DSN` in Vercel. P0 priority in Sprint 41. |
| [P1] | Uptime Monitoring | No external health polling. If Railway/Vercel goes down, no alert. Planned Sprint 44. | Elevate to Sprint 41. Free-tier UptimeRobot for API + web health endpoints (5 min setup). |
| [P1] | Incident Runbooks | Only `docs/runbooks/migration-safety.md` exists. No runbooks for: Redis outage, DB exhaustion, Stripe webhook failure, LLM budget exceeded, DDoS. | Create top 5 incident runbooks before launch. |
| [P1] | On-Call Routing | No PagerDuty/OpsGenie. No defined ownership. | At minimum: Sentry email alerts to `emre@pathforge.eu` for P0 error rates. |
| [P2] | Langfuse Disabled | `llm_observability_enabled: false`. LLM cost/latency/quality invisible. | Activate post-launch when LLM keys are live. |
| [P2] | No Staging | Code goes CI→production. Vercel preview for web, no API staging. | Add Railway staging environment for integration testing. |
| [P2] | VR Baselines | `e2e/__screenshots__/` empty. Visual regression tests skipped in CI. Sprint 44 planned. | Generate and commit baselines via `update-baselines.yml` workflow. |
| [POSITIVE] | Structured Logging | structlog JSON, 14-field redaction, request ID + correlation ID, service metadata. | — |
| [POSITIVE] | Deploy Pipeline | Manual trigger with "deploy" confirmation, pre-flight validation, post-deploy health check. Rollback via Railway. | — |
| [POSITIVE] | Feature Flags | `billing_enabled`, `llm_observability_enabled`, `digest_email_enabled` — config-driven kill switches. | — |

### 2.6 Sprint Completion Validation

**Assessment: ON TRACK (68/100)**

Sprint 39 was the most impactful remediation sprint. Sprints 40-44 address remaining gaps with correct sequencing, except for the items elevated in this audit.

#### Sprint 38 P0 Resolution Status

| Sprint 38 Finding | Status | Resolution Sprint |
|---|---|---|
| P0-1: Password reset flow | ✅ RESOLVED | Sprint 39 |
| P0-2: Email verification | ✅ RESOLVED | Sprint 39 |
| P0-3: Email service (Resend) | ✅ RESOLVED | Sprint 39 |
| P0-4: JWT secret guard bypass | ✅ RESOLVED | Sprint 39 |
| P0-5: Stripe account setup | ⏳ OPEN | Sprint 40 (upcoming, manual) |
| P0-6: LLM API keys | ⏳ OPEN | Sprint 40 (upcoming, manual) |
| P0-7: Pricing SSOT | ✅ RESOLVED | Sprint 39 |
| P0-8: OAuth social login | ✅ RESOLVED | Sprint 39 |

**Result**: 6/8 original P0s resolved. 2 remaining are manual setup tasks (Sprint 40).

#### New Findings Not in Sprint 40-44

| Finding | Priority | Recommended Sprint |
|---|---|---|
| GDPR full account deletion | P0 | Sprint 40 or 41 |
| Token blacklist fail-closed config | P1 | Sprint 41 |

#### Sprint Elevation Recommendations

| Item | Current Sprint | Recommended Sprint | Rationale |
|---|---|---|---|
| Uptime monitoring | Sprint 44 | Sprint 41 | Zero outage visibility without it |
| Security scans blocking | Sprint 44 | Sprint 41 | CVEs can ship to production |
| Refresh token rotation | Sprint 42 | Sprint 41 | 30-day session theft window |

---

## 3. PRIORITIZED REMEDIATION PLAN

### P0 — Must Fix Before Production Launch

| # | Finding | Status | Sprint | Files |
|---|---|---|---|---|
| P0-1 | GDPR full account deletion endpoint | [ACTION REQUIRED] | Add to Sprint 40/41 | `user_profile.py`, `user_profile_service.py` |
| P0-2 | Sentry DSN activation | [ACTION REQUIRED] | Sprint 41 (planned) | Railway + Vercel env vars |
| P0-3 | Stripe account setup | [ACTION REQUIRED] | Sprint 40 (planned) | Manual — Stripe dashboard |
| P0-4 | LLM API key configuration | [ACTION REQUIRED] | Sprint 40 (planned) | Railway env vars |

### P1 — Must Fix Within 2 Sprints of Launch

| # | Finding | Status | Sprint | Files |
|---|---|---|---|---|
| P1-1 | Token blacklist fail-closed policy | [ACTION REQUIRED] | Sprint 41 | `security.py` |
| P1-2 | Refresh token rotation | [ACTION REQUIRED] | Sprint 41 (elevated from 42) | `security.py`, `auth.py` |
| P1-3 | Security scans blocking in CI | [ACTION REQUIRED] | Sprint 41 (elevated from 44) | `ci.yml` |
| P1-4 | Rate limit degradation in health check | [ACTION REQUIRED] | Sprint 41 | `health.py`, `rate_limit.py` |
| P1-5 | Uptime monitoring setup | [ACTION REQUIRED] | Sprint 41 (elevated from 44) | External service config |
| P1-6 | Incident runbooks (top 5) | [ACTION REQUIRED] | Sprint 41 | `docs/runbooks/` |
| P1-7 | Database SSL enabled | [ACTION REQUIRED] | Sprint 41 (planned) | Railway env var |

### P2 — Fix Within 30 Days Post-Launch

| # | Finding | Sprint |
|---|---|---|
| P2-1 | Refresh token → httpOnly cookie | Sprint 42+ |
| P2-2 | Secret rotation documentation | Sprint 42 |
| P2-3 | Circuit breaker in-memory fallback | Sprint 42 |
| P2-4 | N+1 query analysis tooling | Sprint 42 |
| P2-5 | Langfuse activation | Sprint 42+ |
| P2-6 | Staging environment | Sprint 44+ |
| P2-7 | VR baselines committed | Sprint 44 |
| P2-8 | Reviewed ignored CVEs | Sprint 42 |
| P2-9 | Config class decomposition | Backlog |

### P3 — Next Sprint Cycle

| # | Finding |
|---|---|
| P3-1 | Canary/blue-green deployment strategy |
| P3-2 | API response caching for intelligence endpoints |
| P3-3 | Large service file extraction (28KB+ files) |

---

## 4. ARCHITECTURAL DECISIONS LOG

| # | Decision | Rationale | Trade-off |
|---|---|---|---|
| AD-1 | Token blacklist rated P1, not P0 | Redis outage is low-probability; degradation window bounded by access token TTL (60 min). Fail-closed would cause total auth outage during Redis problems. | Accepts temporary revocation bypass for auth availability. |
| AD-2 | CONDITIONAL GO after Sprint 41 | Code quality is high (1,087+ tests, 0 lint/type errors). Remaining gaps are operational activation, not code defects. Sprint 41 addresses critical infrastructure. | Sprints 42-44 polish happens post-soft-launch. |
| AD-3 | localStorage not rated P0 | httpOnly cookie migration requires backend CORS/cookie config changes affecting auth architecture. CSP + SRI mitigate XSS risk. Industry-standard tradeoff. | Accepts browser-local token storage with CSP mitigation. |
| AD-4 | Elevated Sprint 44 items to 41 | Uptime monitoring, security scan blocking, and (recommended) refresh token rotation are too important to defer to post-launch polish. Each takes <1 sprint day. | Sprint 41 scope increases but all items are small. |
| AD-5 | Audit adapted to actual stack | Brief referenced technologies not in codebase. Audit assesses what exists, not what was assumed. Domains restructured for FastAPI/Next.js/RN/Supabase/Stripe. | N/A — correctness over conformance. |

---

## 5. OPEN RISKS REGISTER

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | Redis outage allows revoked tokens | Low | High | P1-1 fail-closed policy + Sprint 41 Redis hardening |
| R2 | Stripe webhook failure in live mode | Medium | High | Sprint 43 verification + webhook failure alerting |
| R3 | LLM provider outage | Medium | Medium | 3-tier fallback chain implemented; monitor via Langfuse |
| R4 | GDPR complaint before account deletion ships | Low | Critical | P0-1 — implement before any production user signup |
| R5 | LLM cost runaway | Low | Medium | Budget guard ($200/mo) exists; add Sentry alert at 80% |
| R6 | Single Railway instance under load | Medium | Medium | Auto-scaling available; rate limit degradation (P1-4) needs addressing |
| R7 | Stolen refresh token — 30-day window | Low | High | P1-2 rotation + future P2-1 httpOnly cookie migration |

---

## 6. VERIFICATION CHECKLIST

Post-remediation verification steps:

- [ ] `DELETE /api/v1/users/me` cascades across all 32 model tables, revokes tokens, cancels Stripe
- [ ] Sentry captures synthetic 500 error with PII scrubbed
- [ ] CI fails when branch has known vulnerable dependency (security scans blocking)
- [ ] `/health/ready` returns 503 with `rate_limiting: degraded` when Redis is down
- [ ] UptimeRobot alerts fire within 5 minutes of service stop
- [ ] Old refresh token rejected after token refresh (rotation)
- [ ] Full smoke test: Register → Verify Email → Login → Upload CV → Career DNA → Checkout → Subscription → Portal → Delete Account

---

## Appendix: Key File References

| File | Relevance |
|---|---|
| `apps/api/app/core/security.py` | JWT creation, token blacklist check (L112-124), `get_current_user` dependency |
| `apps/api/app/core/config.py` | 100+ settings, production validators, feature flags |
| `apps/api/app/core/circuit_breaker.py` | Redis-backed 3-state circuit breaker |
| `apps/api/app/core/rate_limit.py` | SlowAPI with Redis/memory fallback, `RATE_LIMIT_DEGRADED` |
| `apps/api/app/core/middleware.py` | Security headers, request ID, bot trap |
| `apps/api/app/core/logging_config.py` | Structured logging, 14-field redaction |
| `apps/api/app/core/sentry.py` | Error tracking (DSN empty — needs activation) |
| `apps/api/app/core/prompt_sanitizer.py` | 8-layer LLM prompt injection defense |
| `apps/api/app/core/pii_redactor.py` | PII pattern redaction for Langfuse traces |
| `apps/api/app/services/billing_service.py` | Stripe webhook processing, state machine, idempotency |
| `apps/api/app/api/v1/health.py` | Liveness + readiness health checks |
| `apps/api/app/api/v1/auth.py` | Auth routes (login, register, reset, verify) |
| `apps/api/app/api/v1/user_profile.py` | GDPR export routes (missing account deletion) |
| `.github/workflows/ci.yml` | CI pipeline with `continue-on-error` security scan gaps |
| `.github/workflows/deploy.yml` | CD pipeline with manual trigger and health check |
| `docs/ROADMAP.md` | Sprint tracking SSOT |

---

*Report generated 2026-03-19 by autonomous Tier-1 production readiness audit.*
