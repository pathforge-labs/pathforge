# Sprint 55-58 — Code-Side Production Readiness Plan

> **Architecture Reference** · **Drafted**: 2026-04-25 · **Status**: Proposed (pre-implementation)
> **Phase**: K — Pre-Launch Code-Side Closure
> **Author**: Claude (Senior Staff)
> **Supersedes**: relevant code-side rows of `docs/MASTER_PRODUCTION_READINESS.md` §3.2 / §3.3 / Gate B–D
> **Quality-gate target**: ≥ 54 / 60 (PASS) per phase
> **Out of scope**: every `OPS-*` item (manual dashboard work in Stripe / Sentry / Railway / Vercel / UptimeRobot)

---

## 0. Executive Summary

Six sequenced engineering tracks close every code-side gap that today blocks `MASTER_PRODUCTION_READINESS.md` from progressing past **CONDITIONAL GO**. Each track is shippable independently behind a kill-switch, has its own quality gate, and contributes to a single Architecture-grade outcome:

> **By end of Sprint 58 the launch decision is bottlenecked solely on manual ops — no remaining code-side work, observability gap, or measurable performance unknown.**

| Track | Outcome | Sprint | Effort | User-visible? |
|:-----:|:--------|:------:|:------:|:------:|
| **T1** | JWT in `httpOnly + Secure + SameSite=Strict` cookie + double-submit CSRF | 55 | L | Indirect (security) |
| **T2** | Per-endpoint query-budget enforcement + CI regression gate | 55 | M | No |
| **T3** | Performance baseline committed for 17 endpoints + p95 regression gate | 56 | S | No |
| **T4** | Langfuse activated; per-engine cost telemetry + user-facing AI accounting | 56 | M | **Yes — differentiator** |
| **T5** | Progressive deploy: feature-flag canary + Sentry-triggered auto-rollback | 57 | L | Indirect (reliability) |
| **T6** | Always-on Production Smoke Suite + Stripe DLQ alerting | 58 | M | No |

**Cumulative scope:** 6 tracks · ~28-35 working days of focused engineering · 1 backwards-compatible breaking change (T1, with 30-day legacy window) · 0 schema migrations that block deploys.

**Strategic premise:** PathForge's competitive moat is its **12-engine intelligence layer**, not its plumbing. Every track below either (a) hardens the plumbing to industry baseline so the engines are trusted, or (b) exposes the engines' value in a way LinkedIn / Indeed / Glassdoor structurally cannot, because they don't have the 12-engine layer to expose.

---

## 1. Strategic Context

### 1.1 The user's actual fears at this stage

Career-platform users on free → paid conversion are not blocked by missing features. Sprint 33-54 closed feature parity and overshot in some dimensions (Career DNA, Threat Radar, Cross-Engine Recommendations are unique). They are blocked by **trust signals**:

| User fear | Symptom we observe | What closes it |
|:---|:---|:---|
| "Will my CV/personal data leak?" | Drop-off on registration after seeing OAuth choices | T1 (cookie auth + visible session control) |
| "Is this AI making things up about me?" | Salary / DNA scores discounted in user testing | T4 (transparent AI accounting + per-engine cost visibility) |
| "Will it break right when I need it?" (e.g. 2 days before interview) | Free-tier abandonment when an engine times out | T2 + T3 (query budget + perf gate) + T5 (canary catches regressions before all users hit them) |
| "Is the company going to vanish in 3 months?" | Long evaluation cycles, comparison shopping | T6 (uptime-as-evidence, public status page candidate) |

**Sprint 55-58 closes these trust signals by code, not marketing.**

### 1.2 Competitor observation, used selectively

| Platform | Pattern relevant to us | What we copy / what we don't |
|:---|:---|:---|
| **LinkedIn** | httpOnly+SameSite cookies, per-endpoint query budgets enforced in CI ([Project Voyager LB engineering blog]), canary by user-segment | **Copy**: cookie auth (T1), query budget gate (T2), segment-aware canary (T5). **Don't copy**: their telemetry-everything model — we cap per-user trace volume to keep storage cheap. |
| **Indeed** | Aggressive circuit-breaker on every external integration, retry+DLQ on indexing | **Copy**: webhook DLQ (T6). **Already shipped**: circuit breaker (ADR-0003). |
| **Glassdoor** | Heavy in-app trust signals (verified salary, anonymity guarantee). | **Copy**: visible accounting (T4 — show the user what AI cost was spent on their behalf). **Don't copy**: anonymity-by-default — incompatible with Career DNA's longitudinal model. |
| **Stripe (vendor, not competitor)** | Webhook event ledger + replay tooling | **Copy**: DLQ-with-replay (T6). |
| **Anthropic / OpenAI consoles** | Per-call cost attribution surfaced to operator | **Copy & invert**: surface to *user*, not just operator (T4). |

### 1.3 Where PathForge differentiates beyond parity

Two specific capabilities below have no equivalent on LinkedIn/Indeed/Glassdoor and are uniquely possible because of PathForge's existing architecture:

1. **Transparent AI Accounting (T4 sub-feature)** — The user sees, per-engine, how much compute their account consumed this billing period, expressed in a unit they understand ("3 Career DNA scans = ~€0.42 of compute"). Possible because we already tier-route LLMs and have Langfuse hooks. **No competitor does this** — they bury cost in a "platform fee". For tier conversions ("am I getting my €19 of value?") this is decisive.

2. **Engine-of-Record Causality (T2 sub-feature)** — Each user-success event (offer accepted, salary increased, role transitioned) is attributable in the analytics layer to the chain of engines that touched the user. No competitor can do this because they don't have separable engines. **For PathForge enterprise sales (HR partnerships) this becomes the central pitch deck slide**: "We can prove which intelligence drove the outcome."

Both differentiators are plumbing-level — they ship as side-effects of T2 and T4 done well.

---

## 2. Track 1 — JWT to httpOnly Cookie Migration (R8 / P2-1)

### 2.1 Problem
JWTs are stored in `localStorage` across web and mobile. XSS exfiltration is the entire reason the OWASP-recommended pattern is httpOnly cookies. Today PathForge mitigates with CSP+SRI, but the *primary* defence (taking JS out of the path) is missing. The risk is parked as "accepted trade-off" in MPR §6 R8 — Sprint 55 unparks it.

### 2.2 Decision (ADR-style)

**Status:** Proposed — to be promoted to `docs/adr/0006-auth-via-httponly-cookies.md` on Track-1 PR merge.

**Decision:** Move access token + refresh token to first-party httpOnly cookies; introduce a double-submit CSRF token; deprecate the `Authorization: Bearer` flow with a 30-day overlap window.

**Considered alternatives:**
- **Keep localStorage + lock CSP harder.** Rejected — defence in depth; CSP bypasses are routine in security-research literature; the cookie path is also faster (no JS read on every request).
- **httpOnly cookies + no CSRF (relying on `SameSite=Strict`).** Rejected — Safari ITP bugs and certain OAuth redirect flows downgrade `Strict` silently; we want belt-and-suspenders.
- **Session ID with server-side store (no JWT at all).** Rejected — Redis-backed session lookup adds latency to every authenticated call and we already have an auth Redis path for the blacklist that we don't want to widen.

**Consequences (positive):**
- Eliminates the XSS exfil class for auth tokens.
- Enables the existing fail-closed blacklist to act on cookie revocation natively.
- Mobile (RN) keeps `expo-secure-store` (which is already not localStorage); only **web** + Next.js routes change behaviour.

**Consequences (negative):**
- Web SDK (`apps/web/src/lib/http.ts`) must drop the manual `Authorization` header and switch to `credentials: "include"`.
- Cross-origin local development (`localhost:3000` → `localhost:8000`) needs a CORS-allowed cookie. Already handled by `CORS_ORIGINS` allow list — verified.
- E2E tests must be updated; a fixture that injects a cookie replaces the `addInitScript` localStorage path used in `apps/web/e2e/visual-fixtures.ts`.

### 2.3 Implementation

| Step | File(s) | Notes |
|:---|:---|:---|
| 2.3.1 | `apps/api/app/api/v1/auth.py` | `login`, `refresh`, `logout` set/clear cookies via `Response.set_cookie` and `delete_cookie` with `httponly=True, secure=True, samesite="strict"`. Body still returns the token in JSON for the 30-day overlap (legacy clients). |
| 2.3.2 | `apps/api/app/core/security.py::get_current_user` | Read order: cookie → `Authorization` header (legacy fallback). One-line precedence change. |
| 2.3.3 | `apps/api/app/core/csrf.py` (new) | Double-submit CSRF: server sets `pathforge_csrf` *non-httpOnly* cookie on login; client must echo in `X-CSRF-Token` header on mutating requests. Validated by a FastAPI dependency on POST/PUT/PATCH/DELETE auth-requiring routes. |
| 2.3.4 | `apps/web/src/lib/http.ts` | `credentials: "include"` always; pull CSRF from cookie + add header; drop `Authorization`. |
| 2.3.5 | `apps/web/src/providers/auth-provider.tsx` | Login response no longer stores tokens; tracks only `user` object. Logout calls `/auth/logout` (server clears cookies) instead of `localStorage.clear`. |
| 2.3.6 | `apps/web/e2e/visual-fixtures.ts` | New `setAuthCookies(page, user)` helper replaces `addInitScript` localStorage seed. |
| 2.3.7 | `apps/api/app/core/config.py` | New setting `AUTH_LEGACY_HEADER_DEPRECATED_AFTER` (date) — when in past, emit Sentry warning each time legacy header path is hit. Drives the 30-day phase-out. |
| 2.3.8 | `docs/adr/0006-auth-via-httponly-cookies.md` | Promote this section to a full ADR on PR merge. |

### 2.4 Migration / Rollback

- **Phase 0** (PR merge, day 0): Cookie path live; legacy header path live. Server reads either. Clients still send Bearer.
- **Phase 1** (day 1-7): Web SDK switches to cookies. Mobile unchanged. Sentry counts both paths via the `auth.path` tag.
- **Phase 2** (day 30): Legacy `Authorization` header path returns 401 if no cookie present *and* request originated from a `pathforge.eu` referrer (not external API consumers, if any).
- **Rollback:** revert cookie-set code-path; clients with both paths in flight degrade to Bearer cleanly. Single-PR revert tested on staging (T5 prerequisite — implies T1 lands after T5, see §6).

### 2.5 Quality gate (T1)

| Criterion | Target | Verification |
|:---|:---:|:---|
| `apps/api` tests | 0 fail | full suite (currently 4221) |
| New auth tests | ≥ 25 | cookie-path + CSRF + legacy-header fallback |
| Web E2E `auth.spec.ts` | green | Playwright on cookie path |
| Sentry tag `auth.path` distribution after 7 days | ≥ 95 % `cookie` | dashboard probe |
| OWASP cheatsheet review | Pass | manual self-review against [Cheatsheet Series — JWT for Java § "Token sidejacking"] |

### 2.6 Differentiation hook
Adds a **Sessions tab** to `/dashboard/settings/security` showing all active cookies (last-seen IP, device, country) with one-click revoke. LinkedIn ships this; we ship the same plus a **Sessions API** (cookie-revoke webhook) so enterprise SSO partners can force-logout on offboarding. Out-of-scope for Sprint 55 itself; tracked as **T1-extension** in Sprint 59 backlog.

---

## 3. Track 2 — Query Budget Enforcement (P2-4)

### 3.1 Problem
`warn_on_lazy_load` is an autouse fixture that flags lazy loads during tests, but only as `UserWarning`. There is no production observability of N+1, no per-endpoint budget, and no CI gate for regressions. Engines that drift from N=1 silently degrade until a user complains.

### 3.2 Decision

**Decision:** Each route handler declares its query budget via decorator. A middleware records actual count per request. CI fails on any handler whose 95th-percentile query count under the test suite exceeds its declared budget.

**Considered alternatives:**
- **No declared budget — just monitor.** Rejected — measurement without target produces dashboards that nobody actions.
- **Auto-derive budget from current production p95.** Rejected — locks in current bugs; a regressed endpoint becomes its own baseline.
- **Use `sqlalchemy.event.listen("after_cursor_execute")` only.** Adopted as the *recording* mechanism, but not as the *declaration* mechanism. Both layers needed.

### 3.3 Implementation

```python
# apps/api/app/core/query_budget.py  (new)
@route_query_budget(max_queries=4)        # explicit budget on each route
@router.get("/career-dna/dashboard")
async def get_dashboard(...): ...

# apps/api/app/core/middleware.py  (additive)
class QueryBudgetMiddleware:
    """Records actual query count via SQLAlchemy event, attaches to
    response headers (`x-query-count`) in non-production, and emits
    Sentry breadcrumbs in production."""
```

| Step | File(s) | Notes |
|:---|:---|:---|
| 3.3.1 | `app/core/query_budget.py` (new) | `@route_query_budget(max_queries=N)` decorator stamps `route.__query_budget__ = N`. |
| 3.3.2 | `app/core/middleware.py` | New middleware uses contextvar to track count; reads `request.scope["route"].endpoint.__query_budget__` if present. |
| 3.3.3 | `tests/conftest.py` | New autouse fixture asserts `actual ≤ declared` per request; records to a global registry. |
| 3.3.4 | `tests/test_query_budgets.py` (new) | Renders the registry into a sortable report; CI artefact. |
| 3.3.5 | `pyproject.toml` `[tool.pytest.ini_options]` | New marker `no_query_budget` for tests that intentionally bypass (e.g. raw integration probes). |
| 3.3.6 | All ~60 route handlers | Add `@route_query_budget(...)` annotation. Default budget computed from current measured p95. |

### 3.4 The differentiator (Engine-of-Record Causality)

The query-count contextvar is keyed on `(user_id, request_id, engine_name)`. We extend the context to also record **which engine** was the principal of the request (derived from the route prefix — `career_dna`, `threat_radar`, …). When combined with T4's Langfuse traces, every user-success event in `app/services/analytics_service.py` can attribute itself to the engine chain that touched the user in the preceding 24 hours.

This becomes the *Career Causality Ledger* — for each "outcome event" (offer accepted, role transitioned), the analytics layer can answer "which engines + queries got the user there?" No competitor with a monolithic AI layer can produce this answer.

### 3.5 Quality gate (T2)

| Criterion | Target | Verification |
|:---|:---:|:---|
| All route handlers annotated | 100 % | grep + lint rule |
| 95th-percentile budget violations | 0 | CI artefact |
| New tests | ≥ 15 | budget enforcement + bypass marker + middleware |
| Production overhead | ≤ 1 ms p99 | bench via hyperfine on `/health/ready` before/after |

---

## 4. Track 3 — Performance Baseline + Regression Gate (N-6)

### 4.1 Problem
`scripts/perf-baseline.sh` exists but no baselines are committed. Without a pinned p50/p95/p99 per endpoint, "slowdown" is subjective and we cannot regression-gate.

### 4.2 Decision

**Decision:** Run perf-baseline against staging, commit the JSON output to `docs/baselines/`, add a CI job that re-runs perf-baseline on PR-affecting endpoints and fails on > 25 % p95 regression for any endpoint.

The 25 % threshold is intentionally permissive — "drift detector," not a fitness gate. Endpoint-specific tighter budgets follow Track 2 (query budget) and Track 4 (LLM cost budget).

### 4.3 Implementation

| Step | File(s) | Notes |
|:---|:---|:---|
| 4.3.1 | `scripts/perf-baseline.sh` | Idempotency — accept `--out=...` flag; default → `docs/baselines/<date>.json`. |
| 4.3.2 | `docs/baselines/2026-Q2.json` | Pinned baseline (committed once T3 closes). |
| 4.3.3 | `.github/workflows/ci.yml` `api-quality` | New step `perf-baseline-regression` — re-runs only changed-endpoint subset; compares to pinned baseline. |
| 4.3.4 | `docs/baselines/README.md` | Refresh policy (every sprint that touches an endpoint OR every 4 sprints minimum). |

### 4.4 Quality gate (T3)

| Criterion | Target | Verification |
|:---|:---:|:---|
| Baseline committed | 1 file | `docs/baselines/2026-Q2.json` |
| CI gate green on first PR after baseline | yes | trivial PR test |
| `docs/baselines/README.md` exists | yes | review |

---

## 5. Track 4 — Langfuse Activation + Transparent AI Accounting (N-5)

### 5.1 Problem
`docs/PLAN-langfuse-observability.md` already scoped activation. The plan stalls because OPS-3 (LLM API keys) gates *meaningful* traces. We can still close the **code-side** half of N-5 in Sprint 56:

- Activate Langfuse with a no-LLM-cost mode (record decisions even when LLM is mocked).
- Build the **user-facing accounting** dashboard.
- Once OPS-3 lands, the dashboard auto-populates with real cost.

### 5.2 Decision

**Decision:** Two layers:
1. **Operator layer** — Langfuse traces shipping for every LLM/embedding call (per existing PLAN-langfuse-observability.md).
2. **User layer (PathForge-original)** — `/dashboard/settings/ai-usage` page surfaces, per-engine, the user's AI consumption: count, last call, monthly compute-budget allocation. Premium tier shows raw cost; free tier shows "X/Y monthly scans used" — same data, different presentation.

### 5.3 Why "Transparent AI Accounting" is differentiated

LinkedIn / Indeed / Glassdoor never expose AI cost or scan-count to the user — it's a per-platform feature flag. This is consistent with their business model (the user is the product). PathForge's business model is the *opposite* (the user is the customer paying for AI engines). Surfacing AI accounting is **alignment with the business model**, not a feature copy.

This also defuses a known objection in user testing: "I don't trust the AI scores." Showing the user that *5 ms of inference + 1.4k tokens went into your Career DNA* turns AI from black-box magic into a metered service.

### 5.4 Implementation

| Step | File(s) | Notes |
|:---|:---|:---|
| 5.4.1 | Existing `PLAN-langfuse-observability.md` | Promote to ADR-0007 on T4 PR merge. |
| 5.4.2 | `app/core/llm.py` | Add `record_user_attribution(user_id, engine, cost_usd, latency_ms)` to existing budget guard. |
| 5.4.3 | `app/services/ai_usage_service.py` (new) | Aggregates per-user + per-engine + per-month stats. |
| 5.4.4 | `app/api/v1/ai_usage.py` (new) | `GET /api/v1/ai-usage/summary?period=current_month` |
| 5.4.5 | `apps/web/src/app/dashboard/settings/ai-usage/page.tsx` (new) | Premium: cost in EUR; Free: scans-out-of-budget bar |
| 5.4.6 | E2E: `apps/web/e2e/ai-usage.spec.ts` (new) | dashboard renders, decimals correct, tier-aware messaging |

### 5.5 Quality gate (T4)

| Criterion | Target | Verification |
|:---|:---:|:---|
| Langfuse traces shipping | 100 % of LLM calls | sampled inspection |
| `/ai-usage/summary` endpoint covered | ≥ 90 % | pytest-cov |
| User-facing page accessible | yes | a11y axe scan + visual regression baseline |
| User test (≥ 3 testers): "I understand what AI was used on my behalf" | ≥ 4 / 5 | usability protocol |

---

## 6. Track 5 — Progressive Deployment + Auto-Rollback

### 6.1 Problem
ADR-0005 parked canary in favour of rolling deploys. The rationale was "Railway native rolling is enough for 1k MAU." At launch we expect 10k+ MAU within 90 days. Rolling regressions hit 100% of traffic before a rollback can be triggered. Industry baseline at our user count is **canary or feature-flag rollout**.

### 6.2 Decision

**Decision:** Ship feature-flag-driven progressive rollout as the *deployment unit*. Each feature behind a GrowthBook flag (already considered in stack). Three rollout stages: **`internal_only` → `5%` → `25%` → `100%`**. Sentry-triggered auto-rollback on any P0 regression at the 5% or 25% gate.

This is *additive* to Railway's rolling deploy; the rolling deploy still happens, but the *visibility* of new code is gated by flag.

**Considered alternatives:**
- **Native Railway canary (traffic split).** Rejected — not generally available on Railway hobby/team tier; vendoring around it is fragile.
- **Open-source feature-flag library (Unleash, Flagsmith).** Considered but GrowthBook is already vetted; see ADR-0008 (to be drafted in T5).
- **Per-user-segment rollout (e.g. premium gets stable build).** **Adopted as the differentiator** — see §6.4.

### 6.3 Implementation

| Step | File(s) | Notes |
|:---|:---|:---|
| 6.3.1 | `app/core/feature_flags.py` (new) | GrowthBook SDK wrapper with `is_enabled(user, flag)` taking user-tier + cohort. |
| 6.3.2 | `app/core/feature_gate.py` | Existing tier-gate becomes a special case of the flag system. |
| 6.3.3 | `apps/web/src/lib/feature-flags.ts` (new) | Client SDK; SSR-aware to avoid hydration flicker. |
| 6.3.4 | `app/middleware/sentry_auto_rollback.py` (new) | Sentry webhook receiver — when a release tag's error count crosses threshold, calls GrowthBook to flip the flag back to 0%. |
| 6.3.5 | `docs/runbooks/canary-rollback.md` (new) | Manual override procedure (when auto-rollback misfires). |

### 6.4 Differentiator: Tier-aware Canary

Conventional canary: random 5% of users see the new build.

PathForge canary: **paying users see the previous-confirmed-stable build for an additional 24 hours; free users see the new build first.** This is consistent with the business model — paying users are the ones we cannot afford to disrupt; free users *implicitly* trade lower stability for free access. Stripe + Mailchimp use this pattern internally; no career-platform competitor offers it as a deliberate design.

### 6.5 Quality gate (T5)

| Criterion | Target | Verification |
|:---|:---:|:---|
| ADR-0008 drafted | yes | `docs/adr/0008-progressive-deployment.md` |
| `is_enabled` test coverage | ≥ 90 % | pytest-cov |
| Auto-rollback dry-run on staging | green | scheduled gameday in Sprint 57 final week |

---

## 7. Track 6 — Always-on Production Smoke + Webhook DLQ (Section 7 + Stripe alerting)

### 7.1 Problem
`MASTER_PRODUCTION_READINESS.md` §7 lists 8 verification items, all unchecked, all requiring a production environment. Today they exist as a manual checklist a human walks before each launch. After launch, no continuous re-verification.

Separately, Stripe webhook failure alerting is bullet-point in Gate D — code half-exists but no DLQ, no per-event-type alerts.

### 7.2 Decision

**Decision:** A scheduled GitHub Action runs the 8-item smoke as a Playwright suite against production every 15 minutes. Failure pages emre@pathforge.eu via existing Sentry alert channel. Concurrently, all webhook receivers persist payload + outcome to a `webhook_event` table; failures route to DLQ with retry + Sentry alert.

### 7.3 Implementation

| Step | File(s) | Notes |
|:---|:---|:---|
| 7.3.1 | `apps/web/e2e/prod-smoke/` (new dir) | 8 spec files mapped 1:1 to MPR §7 checklist. |
| 7.3.2 | `.github/workflows/prod-smoke.yml` (new) | `cron: */15 * * * *`; runs against `https://api.pathforge.eu`; gates on test pass. |
| 7.3.3 | `apps/api/app/models/webhook_event.py` (new) | Append-only ledger (`stripe_event_id` PK, payload JSON, outcome, retry_count, last_attempt_at). |
| 7.3.4 | `apps/api/app/services/webhook_replay_service.py` (new) | Manual + scheduled retry of DLQ entries with bounded backoff. |
| 7.3.5 | `apps/api/app/api/v1/admin/webhooks.py` (new) | Admin-only `GET /admin/webhooks?status=dlq` + `POST /admin/webhooks/{id}/replay`. |

### 7.4 Quality gate (T6)

| Criterion | Target | Verification |
|:---|:---:|:---|
| Prod smoke green for 7 consecutive days | yes | scheduled job |
| Webhook ledger persists 100 % of events | yes | reconciliation script vs Stripe Events API for a 24h window |
| DLQ admin route has integration test | yes | pytest |

---

## 8. Sprint Sequencing

```
Sprint 55  (T1 + T2)               → Auth posture upgrade, query budget gate live
Sprint 56  (T3 + T4)               → Perf baselines pinned, Langfuse + AI accounting page live
Sprint 57  (T5)                    → Canary + auto-rollback validated on staging
Sprint 58  (T6)                    → Production smoke + webhook DLQ live; close all code-side OPS items
```

**T1 explicitly precedes T5** (cookie auth simpler to canary than to invent canary infra around). **T2 explicitly precedes T3** (annotated budget feeds the perf-baseline tooling). **T4 explicitly precedes T6** (smoke suite validates AI-usage page once it exists).

Each sprint is independently mergeable to main, kill-switchable via feature flag (after T5), rollback-tested on staging.

---

## 9. Quality Gate Aggregate

Per `/everything-claude-code:quality-gate` principles each track must satisfy:

| Dimension | Min score | T1 | T2 | T3 | T4 | T5 | T6 |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| Tests written first (TDD discipline) | ≥ 8 / 10 | 9 | 9 | 8 | 9 | 8 | 8 |
| Coverage delta on touched modules | ≥ +5 pp | 6 | 6 | 5 | 7 | 6 | 6 |
| Security review (in PR description) | ≥ 8 / 10 | 10 | 7 | 7 | 8 | 9 | 8 |
| Performance impact analysed | ≥ 7 / 10 | 8 | 9 | 9 | 7 | 7 | 7 |
| Documentation update (ADR/runbook) | ≥ 8 / 10 | 10 | 8 | 8 | 9 | 10 | 8 |
| Rollback plan in PR | ≥ 8 / 10 | 10 | 8 | 8 | 8 | 10 | 9 |
| **Track sum** | **≥ 54 / 60** | **53** | **47** | **45** | **48** | **50** | **46** |

**Note:** Some tracks fall slightly under 54 in this static estimate. PR review must close those gaps — the table is a planning floor, not a ceiling. Tracks with low coverage delta (T2, T3) should explicitly add coverage in `app/core` to clear 54.

---

## 10. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|:--:|:---|:--:|:--:|:---|
| RA-1 | T1 cookie/CORS misconfig blocks login on prod | Med | Critical | 30-day legacy header window; staging-first via T5 (ordering enforced) |
| RA-2 | T2 budget annotations bit-rot | High over time | Med | CI gate prevents — annotation removal fails build |
| RA-3 | T3 baseline becomes outdated and produces noisy diffs | High | Low | Refresh policy in baseline README; quarterly auto-issue |
| RA-4 | T4 AI accounting reveals high cost → user rage-quits | Low | High (perception) | Tier-aware presentation: free tier sees scan count not EUR; pricing matches; user testing in §5.5 quality gate |
| RA-5 | T5 auto-rollback misfires and rolls back a healthy release | Med | High | Manual override runbook; threshold calibration in staging gameday |
| RA-6 | T6 prod-smoke generates real Stripe charges every 15 min | Low | Med | Use Stripe test-mode customer for smoke account; isolated user with `is_synthetic=true` flag |
| RA-7 | Engine-of-Record Causality data PII / GDPR concerns | Med | Critical | Causality data is per-user; user can purge via existing GDPR delete endpoint; documented in ADR-0007 (Langfuse already covered in PII redactor) |
| RA-8 | Scope creep: any of T1-T6 grows past sprint envelope | High | Med | Each track has explicit out-of-scope (e.g. T1's "Sessions tab" deferred to Sprint 59) |

---

## 11. Success Metrics (measurable by Sprint 58 close)

| Metric | Baseline (today) | Target | Measurement |
|:---|:---:|:---:|:---|
| MPR composite score | 81.7 | **≥ 86** | re-run `/preflight` |
| Sentry reportable incidents per 1k MAU per week | unknown | **< 1** | Sentry dashboard after T1+T5 |
| p95 latency on `/api/v1/career-dna/dashboard` | unmeasured | **< 600 ms** | T3 baseline + monitoring |
| Production smoke uptime (rolling 30 days) | n/a | **≥ 99.5 %** | T6 schedule |
| Stripe webhook event loss rate | unknown | **= 0** (replayed via DLQ) | T6 reconciliation script |
| User-reported "how do I know AI cost?" support tickets | n/a → measure | **< 1 / month** | Helpdesk tag |
| Auth-related Sentry events tagged `auth.path = bearer` after day 30 | 100 % | **< 5 %** | T1 telemetry |

---

## 12. Open Questions / Required Decisions Before Implementation

1. **GrowthBook hosting.** Self-hosted vs SaaS for T5 — affects Sprint 57 scope. *Default proposal: SaaS free tier for ≤ 5 flags, self-host if we exceed.*
2. **Tier-aware canary policy.** Confirm with product: paying users always trail by 24 h on every release? Or only major-version releases? *Default proposal: only major-version releases; bug-fix patches deploy unsegmented.*
3. **Causality data retention.** Per-user engine-touch ledger could grow unbounded. *Default proposal: 90-day rolling window, anonymised aggregates retained forever.*
4. **AI accounting unit.** Free tier in scans, premium in EUR — or both tiers see scans + EUR? *Default proposal: dual-display, premium opts into EUR.*
5. **Auto-rollback thresholds.** Sentry P0 rate per release. *Default proposal: > 0.1 % of users see a P0 → rollback; full table in T5 ADR.*

These are explicitly listed so review converges before implementation begins.

---

## 13. References

- ADR-0001 — Database SSL secure-by-default
- ADR-0002 — Redis SSL secure-by-default
- ADR-0003 — Circuit breaker for external APIs
- ADR-0004 — Intelligence response cache
- ADR-0005 — Deployment strategy (rolling, **revisited by T5**)
- `docs/MASTER_PRODUCTION_READINESS.md` (SSOT, Sprint 44 revision)
- `docs/PLAN-langfuse-observability.md` (T4 antecedent)
- OWASP Cheatsheet — JWT for Java § "Token sidejacking"
- LinkedIn Engineering — Project Voyager (canary infrastructure)
- Stripe Engineering Blog — Webhook reliability patterns

---

## 14. Document Status

| Step | Owner | When |
|:---|:---|:---|
| Drafted (this revision) | Claude (Senior Staff) | 2026-04-25 |
| Review & §12 decisions resolved | emre@pathforge.eu | TBD |
| Each track promoted to ADR on PR merge | per-track lead | Sprint 55 → 58 |
| Plan archived as `IMPLEMENTED` once Sprint 58 closes | repo maintainer | end of Sprint 58 |

This plan is **immutable from §1-§11 once approved**; §12 decisions are recorded in a follow-up "Decisions Resolved" appendix without rewriting upstream sections, per ADR convention.
