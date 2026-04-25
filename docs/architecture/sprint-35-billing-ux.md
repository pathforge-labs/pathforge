# Sprint 35 — Revenue Integrity, Billing UX & Observability Hardening

> **Date**: 2026-03-02 | **Authority**: Senior Staff Engineer | **Sprint**: 35
> **Focus**: Frontend Billing UI + Backend Test Coverage + Frontend Error Monitoring + Visual Regression

---

## 1. Context & Motivation

Sprint 34 established the complete backend billing infrastructure: Stripe SDK integration,
webhook processing, idempotent event logging, state machine transitions, feature gating,
checkout session creation, and customer portal sessions. All 7 endpoints and the webhook
handler are production-ready with audit findings (F1–F35) resolved.

**Sprint 35 connects this backend to the user-facing web experience.**

The revenue pipeline is incomplete without:

1. A pricing page where users compare plans and initiate checkout
2. A billing status view showing current plan, usage, and renewal
3. A Stripe Customer Portal redirect for subscription management
4. Frontend error monitoring (`@sentry/nextjs`) matching the backend's Sentry setup
5. Backend test coverage for all Sprint 34 modules (currently at 0 tests)
6. Visual regression baselines for monetization-critical pages

---

## 2. Architecture Principles

| #   | Principle                        | Implementation                                                                  |
| :-- | :------------------------------- | :------------------------------------------------------------------------------ |
| A1  | **DB is source of truth**        | Frontend reads subscription state from API, never from Stripe SDK               |
| A2  | **UI gating is informational**   | Frontend shows/hides features based on API response; API enforces               |
| A3  | **No client-side pricing**       | Tier IDs and prices come from config, checkout session created server-side      |
| A4  | **Separation of concerns**       | Billing UI is isolated from intelligence modules                                |
| A5  | **Idempotent webhooks**          | Already implemented (Sprint 34 F2); tests will verify                           |
| A6  | **No PII in telemetry**          | Sentry `denylist` extends backend pattern; no Stripe tokens in breadcrumbs      |
| A7  | **Config-driven feature matrix** | `TIER_ENGINES` / `TIER_SCAN_LIMITS` exposed to frontend via `/billing/features` |

---

## 3. System Design

### 3.1 Data Flow

```
User → Pricing Page → POST /billing/checkout → Stripe Checkout → Stripe Webhook → DB → GET /billing/subscription → Billing Status UI
                                                                                           ↓
User → Settings/Billing → POST /billing/portal → Stripe Customer Portal → Stripe Webhook → DB
                                                                                           ↓
User → Dashboard Feature → GET /billing/features → Feature Gate (API enforced) → 403 or 200
```

### 3.2 Existing Backend API Surface (Sprint 34)

| Endpoint                | Method | Purpose                 | Frontend Consumer        |
| :---------------------- | :----- | :---------------------- | :----------------------- |
| `/billing/subscription` | GET    | Current plan state      | Billing Status UI        |
| `/billing/usage`        | GET    | Scan usage this period  | Billing Status UI        |
| `/billing/features`     | GET    | Engine access matrix    | Feature gating display   |
| `/billing/checkout`     | POST   | Create Checkout session | Pricing Page             |
| `/billing/portal`       | POST   | Create Portal session   | Settings → Billing       |
| `/billing/events`       | GET    | Admin billing log       | Admin dashboard (future) |
| `/webhooks/stripe`      | POST   | Stripe webhook handler  | N/A (server-to-server)   |

### 3.3 Pricing Tiers (from `feature_gate.py`)

| Tier    | Price     | Scan Limit | Engines                                             |
| :------ | :-------- | :--------- | :-------------------------------------------------- |
| Free    | €0/mo     | 3/month    | career_dna, threat_radar                            |
| Pro     | €14.99/mo | 30/month   | + 8 engines (skill_decay, salary, simulation, etc.) |
| Premium | €29.99/mo | Unlimited  | + career_passport, predictive_career                |

### 3.4 Frontend Component Architecture

```
apps/web/src/
├── types/api/billing.ts              ← TypeScript interfaces
├── lib/api-client/billing.ts         ← API client functions
├── hooks/api/use-billing.ts          ← React Query hooks
├── config/pricing.ts                 ← Config-driven pricing data
├── components/billing/
│   ├── PricingCard.tsx               ← Individual tier card
│   ├── PricingGrid.tsx               ← 3-tier comparison grid
│   ├── BillingStatusCard.tsx         ← Current plan + usage
│   ├── UsageProgressBar.tsx          ← Scan usage visualization
│   └── UpgradeCTA.tsx                ← Reusable upgrade prompt
├── app/(marketing)/pricing/page.tsx  ← Public pricing page
├── app/(dashboard)/dashboard/settings/billing/page.tsx  ← Billing management
└── app/global-error.tsx              ← Sentry error boundary
```

---

## 4. Competitor Analysis & Differentiation

### 4.1 LinkedIn Premium Model

- **LinkedIn**: Opaque pricing, no public feature matrix, forced trial-to-paid funnel
- **PathForge**: Transparent tier comparison, config-driven feature matrix, no dark patterns
- **Differentiation**: Full usage visibility, per-engine breakdown, honest scan limits

### 4.2 Stripe Best Practices (from Stripe docs)

- Server-side session creation (never trust client plan IDs)
- Webhook-driven subscription management (not polling)
- Customer Portal for self-service (no internal billing UI reimplementation)
- Signature verification on all webhooks
- **PathForge follows all of these** — Sprint 34 backend already compliant

### 4.3 SaaS Pricing Page Standards

- **Three-tier layout** with highlighted "recommended" tier (industry standard)
- **Annual/monthly toggle** with savings callout
- **Feature comparison table** below cards for detailed comparison
- **Clear CTA hierarchy**: Free signup / Try Pro / Go Premium
- **Mobile-responsive**: Cards stack vertically on small screens
- **Accessibility**: WCAG 2.1 AA compliant, keyboard navigable, screen reader labels

---

## 5. Workstream Breakdown

### WS-1: Frontend Billing Types + API Client + Hooks

**Files**: 3 new files

Establishes the TypeScript data layer following existing patterns (22 type files, 22 API clients, 15 hooks).

### WS-2: Pricing Configuration

**Files**: 1 new file

Config-driven pricing data. Feature matrix sourced from a single constant (mirrors `TIER_ENGINES` / `TIER_SCAN_LIMITS`). Not hardcoded in JSX.

### WS-3: Pricing Page

**Files**: 3–4 new component files + 1 page route

Public marketing page at `/pricing`. Three-tier comparison with monthly/annual toggle, feature comparison, highlighted recommended tier, clear CTAs, responsive layout.

### WS-4: Billing Status UI

**Files**: 2–3 new component files + 1 page route

Dashboard page at `/dashboard/settings/billing`. Shows current plan, renewal date, usage bar, engine access summary, upgrade/manage CTAs. Links to Stripe Customer Portal.

### WS-5: Backend Test Coverage

**Files**: 4–5 new test files

Test coverage for Sprint 34 modules:

- `test_billing.py` — full billing API lifecycle (checkout, subscription, usage, portal, events)
- `test_feature_gate.py` — tier→engine enforcement, bypass prevention
- `test_admin.py` — admin endpoint permission checks
- `test_waitlist.py` — waitlist CRUD + conversion
- `test_public_profile.py` — profile visibility + privacy controls

Target: ≥90% coverage on billing module.

### WS-6: Frontend Sentry Integration

**Files**: 4–5 new/modified files

`@sentry/nextjs` setup with:

- `sentry.client.config.ts` + `sentry.server.config.ts`
- `next.config.ts` wrapped with `withSentryConfig`
- CSP update for Sentry ingest domain
- `global-error.tsx` error boundary
- Environment-separated DSN (env var)
- PII denylist matching backend pattern
- Release tagging

### WS-7: Visual Regression Baselines

**Files**: 1 new E2E spec + baseline screenshots

Playwright spec capturing snapshots:

- Pricing page (3-tier layout)
- Billing status UI (active plan)
- Public profile page
- Lighthouse performance scores stored in `docs/baselines/`

---

## 6. Security Checklist

- [ ] Stripe webhook signature verification (Sprint 34 — test in WS-5)
- [ ] No Stripe secret keys in client bundle (env var separation)
- [ ] All billing endpoints require authentication (test in WS-5)
- [ ] Plan IDs validated server-side (test in WS-5)
- [ ] Checkout session tampering protection (server-side price resolution)
- [ ] Admin billing event endpoint requires admin role (test in WS-5)
- [ ] Sentry DSN is NOT a secret (public by design) but PII is scrubbed
- [ ] CSP updated to allow `*.ingest.sentry.io` and `checkout.stripe.com`
- [ ] Rate limiting on billing mutation endpoints (10/min)
- [ ] Checkout URL domain validation restricts to `frontend_url`
- [ ] Portal session includes `return_url`
- [ ] `@sentry/nextjs` compatible with Next.js v16 + React 19
- [ ] Sentry env vars documented in `.env.example`
- [ ] `frontend_url` added to API config

---

## 7. Performance Targets

| Metric                    | Target      | Measurement         |
| :------------------------ | :---------- | :------------------ |
| Checkout session creation | < 500ms P95 | Backend test timing |
| Billing status fetch      | < 300ms P95 | Backend test timing |
| Webhook processing        | < 500ms     | Backend test timing |
| Pricing page load         | < 1.5s P95  | Lighthouse          |

---

## 8. Explicit Non-Goals

- No AI feature expansion
- No charting libraries (Career Resilience trend line stays deferred)
- No mobile Sentry (`sentry-expo` stays deferred)
- No OCR (Image-to-document stays deferred)
- No referral system, marketing automation, search indexing
- No target role form or workflow drill-down modal
- No new intelligence logic changes

---

## 9. Tier-1 Production Audit Findings

### Security (S)

| ID     | Severity  | Finding                                                                                                                                                                          | Action                                                                     |
| :----- | :-------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------- |
| **S1** | 🔴 High   | `POST /billing/checkout` and `POST /billing/portal` have **no rate limiter** — unlike admin endpoints which use `@limiter.limit`. Allows automated checkout session brute-force. | Add `@limiter.limit("10/minute")` on both mutation endpoints.              |
| **S2** | 🟡 Medium | `success_url` and `cancel_url` in `CreateCheckoutSessionRequest` accept **arbitrary URLs** (only `min_length=1, max_length=2048`). Attacker could pass phishing domain.          | Add Pydantic validator restricting URLs to `settings.frontend_url` origin. |
| **S3** | 🟡 Medium | CSP `connect-src` missing `*.ingest.sentry.io` and `frame-src` missing `checkout.stripe.com` (Stripe Checkout may use iframe in some flows).                                     | Update `next.config.ts` CSP directives.                                    |
| **S4** | 🟢 Info   | `billing_enabled` kill switch (F1) only checked in checkout/portal — `get_features` still returns tier data when billing off.                                                    | By design (informational gating). Add inline code comment.                 |

### Reliability (R)

| ID     | Severity  | Finding                                                                                                                                       | Action                                                                         |
| :----- | :-------- | :-------------------------------------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------- |
| **R1** | 🟡 Medium | `create_portal_session` omits `return_url` — after portal, user redirected to Stripe default (not PathForge).                                 | Add `return_url` to `stripe.billing_portal.Session.create()`.                  |
| **R2** | 🟡 Medium | No **checkout return handler**. After Stripe redirects to `success_url?session_id=...`, no query invalidation triggers to refresh billing UI. | Add URL param handler that calls `queryClient.invalidateQueries(["billing"])`. |
| **R3** | 🟢 Info   | Webhook error handler (L232-245) lacks explicit `db.rollback()` — relies on SQLAlchemy session close.                                         | Acceptable pattern. Add code comment.                                          |

### Frontend Architecture (FA)

| ID      | Severity  | Finding                                                                    | Action                                                              |
| :------ | :-------- | :------------------------------------------------------------------------- | :------------------------------------------------------------------ |
| **FA1** | 🟡 Medium | No `global-error.tsx` exists — Next.js needs this for root error boundary. | Already planned in WS-6.                                            |
| **FA2** | 🟢 Low    | Pricing page lacks JSON-LD structured data for Google rich results.        | Add `<script type="application/ld+json">` in pricing page metadata. |

### Config Integrity (CI) / Test Infrastructure (TI)

| ID      | Severity  | Finding                                                                                                          | Action                                                                               |
| :------ | :-------- | :--------------------------------------------------------------------------------------------------------------- | :----------------------------------------------------------------------------------- |
| **CI1** | 🟡 Medium | Frontend `pricing.ts` and backend `feature_gate.py` contain **duplicate engine lists** — manual sync drift risk. | Add test validating frontend config matches `/billing/features` response shape.      |
| **TI1** | 🟡 Medium | No Stripe SDK mock fixture in API `tests/conftest.py`. All billing tests need shared `mock_stripe` fixture.      | Create billing-specific fixtures in `conftest.py` or separate `conftest_billing.py`. |

### Final Audit Pass — Dependency & Infrastructure (D/I)

| ID     | Severity    | Finding                                                                                                                                                                                                    | Action                                                                              |
| :----- | :---------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------- |
| **D1** | 🔴 High     | `@sentry/nextjs` **not in** `package.json`. Next.js v16.1.6 + React 19 compatibility must be verified. If unsupported, use `@sentry/react` + manual instrumentation.                                       | `pnpm add @sentry/nextjs` in WS-6. Verify compatibility.                            |
| **D2** | 🟡 Medium   | **No toast library** installed — `sonner` (shadcn-compatible) needed for checkout feedback (R2).                                                                                                           | `pnpm add sonner`, add `<Toaster />` to root layout. WS-4 prerequisite.             |
| **D3** | 🟡 Medium   | **No `typecheck` script** in `package.json` — verification plan command will fail.                                                                                                                         | Add `"typecheck": "tsc --noEmit"` or adjust verification commands.                  |
| **I1** | 🟡 Medium   | S2 URL validator needs `frontend_url`. `cors_origins_production` already has `pathforge.eu` — add `frontend_url` as a `@property` derived from `cors_origins_production[0]` rather than a duplicate field. | Add `@property frontend_url` to `Settings` deriving from `cors_origins_production`. |
| **I2** | 🟡 Medium   | **Sentry env vars** missing from `.env` and `.env.example`: `NEXT_PUBLIC_SENTRY_DSN`, `NEXT_PUBLIC_SENTRY_ENVIRONMENT`.                                                                                    | Add Sentry block to `.env.example` and `.env.local`.                                |
| **I3** | 🟢 Info     | Sidebar nav hardcoded in `layout.tsx` — billing is a settings sub-route, not a top-level item. No sidebar change needed.                                                                                   | By design (ADR-035-03).                                                             |
| **I4** | 🟢 Low      | **No frontend billing hooks tests** planned. WS-1 creates 3 files with no Vitest coverage.                                                                                                                 | Add `use-billing.test.ts` with mock API responses.                                  |
| **I5** | 🟢 Low      | Checkout URLs should use `APP_URL` from `brand.ts` — not hardcoded strings.                                                                                                                                | Use `${APP_URL}/dashboard/settings/billing?...` pattern.                            |
| **I6** | ✅ Verified | `FeatureAccessResponse` schema shape matches `get_features` return dict — TypeScript types will align.                                                                                                     | No action needed.                                                                   |

### Third Audit Pass — Architectural Corrections (AC)

| ID      | Severity  | Finding                                                                                                                                                                                                  | Action                                                                                                                          |
| :------ | :-------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | :------------------------------------------------------------------------------------------------------------------------------ |
| **AC1** | 🟡 Medium | `query-keys.ts` has **no `billing` domain** — all 5 billing hooks need query keys.                                                                                                                       | Add `billing: { all, subscription, usage, features }` block to `query-keys.ts`. WS-1.                                           |
| **AC2** | 🟡 Medium | `next.config.ts` wraps as `analyze(nextConfig)` — Sentry wrapper must **compose correctly**: `analyze(withSentryConfig(nextConfig, sentryOptions))`. Wrong order breaks source maps and bundle analysis. | Specify compose order in WS-6 as `analyze(withSentryConfig(nextConfig))`.                                                       |
| **AC3** | 🟡 Medium | `billing_enabled: bool = False` in config — pricing page must **gracefully degrade** when billing is disabled (show plans without checkout buttons, or show "Coming Soon" badge).                        | Add `billing_enabled` check in pricing page. Use `useFeatures()` hook or dedicate a `fetchPublic` check to `/billing/features`. |
| **AC4** | 🟡 Medium | `config.py` has no `rate_limit_billing` setting — WS-0 hardcodes `"10/minute"` in decorators. Should use config-driven rate limit.                                                                       | Add `rate_limit_billing: str = "10/minute"` to `Settings` and reference in billing routes.                                      |
| **AC5** | 🟢 Low    | `conftest.py` already provides `auth_client` fixture — billing tests must reuse it, not create parallel fixtures.                                                                                        | Use existing `auth_client` in billing tests.                                                                                    |
| **AC6** | 🟢 Low    | `fetchPublic()` exists in `http.ts` for unauthenticated calls — pricing page `useFeatures` must use `fetchPublic` for unauthenticated users, `fetchWithAuth` for authenticated.                          | Implement dual-path: `fetchPublic("/api/v1/billing/features")` for pricing, `fetchWithAuth` for billing status.                 |
| **AC7** | 🟢 Low    | `api-client/index.ts` barrel exports all API clients — new `billing.ts` must be registered there.                                                                                                        | Add `export { billingApi } from './billing'` to barrel.                                                                         |

---

## 10. ADR Log

| ID         | Decision                               | Rationale                                                                            |
| :--------- | :------------------------------------- | :----------------------------------------------------------------------------------- |
| ADR-035-01 | Use `@sentry/nextjs` wizard pattern    | Official Sentry Next.js SDK, auto-instruments routes and API handlers                |
| ADR-035-02 | Config-driven pricing (not DB-driven)  | Matches `feature_gate.py` pattern; DB-driven is future enhancement                   |
| ADR-035-03 | Billing page as settings sub-route     | Users expect billing under Settings, not a standalone page                           |
| ADR-035-04 | Pricing page as marketing route        | Public page (no auth required), follows existing marketing layout                    |
| ADR-035-05 | Playwright for visual regression       | Already used for 8 E2E specs; no new dependency                                      |
| ADR-035-06 | Rate limit billing mutations at 10/min | Prevents automated session brute-force; matches admin endpoint precedent (S1)        |
| ADR-035-07 | Domain-restrict checkout URLs          | `success_url` / `cancel_url` must match `settings.frontend_url` origin (S2)          |
| ADR-035-08 | Add `return_url` to portal session     | Ensures Stripe portal redirects back to PathForge billing page (R1)                  |
| ADR-035-09 | `frontend_url` as `@property`          | Derive from `cors_origins_production[0]` — single source, no duplication (AC1/I1)    |
| ADR-035-10 | Sentry compose order                   | `analyze(withSentryConfig(nextConfig))` — Sentry wraps inner, analyzer outer (AC2)   |
| ADR-035-11 | Billing-disabled graceful degradation  | Pricing page shows plans with "Coming Soon" badge when `billing_enabled=false` (AC3) |
| ADR-035-12 | Config-driven rate limits              | `rate_limit_billing` in `config.py` instead of hardcoded decorator strings (AC4)     |
