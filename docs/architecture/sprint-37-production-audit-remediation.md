# Sprint 37 — Production Audit Remediation & CI Green

> **Architecture Reference** | Finalized: 2026-03-03 (3-round Tier-1 audit)
> **Phase**: J — Production Maturity & Polish
> **Sprint Goal**: Full CI green, pricing page CSS restoration, VR test infrastructure hardening, MyPy compliance, Gemini Code Assist enhancements

---

## Sprint Context

Sprint 37 resolves all critical findings from the Tier-1 production audit (2026-03-03). Three rounds of audit identified and corrected errors across 9 findings, resulting in a fully source-verified implementation plan.

---

## Audit Findings (9 Items)

| #   | Finding                                                                      | Severity |
| :-- | :--------------------------------------------------------------------------- | :------- |
| F1  | 31 BEM CSS selectors missing for pricing page                                | CRITICAL |
| F2  | `/api/v1/billing/features` unmocked in VR → pricing renders as "Coming Soon" | CRITICAL |
| F3  | VR CI: no baselines + 15s timeout too low                                    | HIGH     |
| F4  | Title doubles: `Pricing \| PathForge \| PathForge`                           | MEDIUM   |
| F5  | Growth vector worker is stubbed                                              | MEDIUM   |
| F6  | CSP `connect-src` missing `localhost:8000`                                   | LOW      |
| F7  | MyPy is `continue-on-error: true`                                            | MEDIUM   |
| F8  | Gemini config missing Alembic ignore                                         | LOW      |
| F9  | Styleguide missing error/branch patterns                                     | LOW      |

---

## Dual Pricing Architecture

```
Landing page (/, /comparison):
  PricingCards → pricing-card-standard, pricing-card-popular
  CSS: globals.css:1241-1403 ✅

Pricing page (/pricing):
  PricingGrid → PricingCard → pricing-card__*, pricing-grid__*
  CSS: MISSING ❌ → WS-1
```

These are intentionally separate: the landing page is marketing-focused (no auth, no billing API), while the pricing page is billing-integrated (feature flags, Stripe checkout, scan limits).

---

## VR Auth Chain

```
1. addInitScript → localStorage(pathforge_access_token, exp=2286)
2. hasTokens() → true
3. fetchWithAuth('/api/v1/users/me') → http://localhost:8000
4. Playwright route interceptor → MOCK_USER (200)
5. dispatch SET_AUTHENTICATED ✅
```

JWT exp=2286 prevents 401. Auth refresh mock is defensive only.

---

## Missing VR Mocks (F2)

```
/api/v1/billing/features → PricingPageClient → billingEnabled
/api/v1/auth/refresh     → refresh-queue.ts (defensive)
/api/v1/auth/login       → auth-provider.tsx (defensive)
/api/v1/auth/logout      → auth-provider.tsx (defensive)
```

| Route                      | Consumer               | Mock Shape                                       |
| :------------------------- | :--------------------- | :----------------------------------------------- |
| `/api/v1/billing/features` | `PricingPageClient:27` | `{ tier, engines, scan_limit, billing_enabled }` |
| `/api/v1/auth/refresh`     | `refresh-queue.ts:51`  | `{ access_token, refresh_token, token_type }`    |

> **Note**: F2b — The mock shape was corrected in Audit Round 3. `FeatureAccessResponse` requires `{ tier, engines, scan_limit, billing_enabled }`, NOT `{ billing_enabled, features }`.

---

## Growth Vector Pipeline

```
worker.py::recalculate_intelligence(user_id)
  → CareerDNAService.generate_full_profile(db, user_id=uuid, dimensions=["growth_vector"])
    → @staticmethod: _gather_experience_text, _gather_explicit_skills, _gather_preferences_text
    → _compute_growth_vector(db, career_dna, ...)
    → CareerDNAAnalyzer.compute_growth_vector(...)
```

> **Corrected in Round 2**: `CareerDNAService.compute_dimensions()` does NOT exist. The correct API is `generate_full_profile`.
> **Corrected in Round 3**: Worker.py is missing `import uuid`.

---

## Session Factory

`app.core.database.async_session_factory` — verified at `database.py:51`.

---

## MyPy: 14 Errors in 9 Files

7× `unused-ignore`, 2× `misc` (BaseSettings/Any return), 5× other patterns. ~30min fix.

---

## CI `continue-on-error` Audit (5 Instances)

| Line | Step            | Current | Target                          |
| :--- | :-------------- | :------ | :------------------------------ |
| 79   | MyPy            | `true`  | **Remove** (WS-9)               |
| 98   | pip-audit       | `true`  | Keep (external deps)            |
| 187  | VR job          | `true`  | **Remove** after WS-7 baselines |
| 231  | VR tests step   | `true`  | **Remove** after WS-7 baselines |
| 242  | Perf tests step | `true`  | **Remove** after WS-7 baselines |

---

## Workstream Summary

| WS    | Title                               | Priority | Key Corrections                                 |
| :---- | :---------------------------------- | :------- | :---------------------------------------------- |
| WS-1  | Pricing page BEM CSS (31 selectors) | CRITICAL | Legacy CSS is NOT dead code                     |
| WS-2  | VR mock completeness                | CRITICAL | F2 discovered, mock shape corrected             |
| WS-3  | VR CI resilience                    | HIGH     | Expanded to `playwright.config.ts`              |
| WS-4  | CSP dev fix                         | LOW      | —                                               |
| WS-5  | Title dedup                         | MEDIUM   | Also remove orphaned `pageTitle` import         |
| WS-6  | Growth vector worker                | MEDIUM   | API: `generate_full_profile`, add `import uuid` |
| WS-7  | CI baseline bootstrap               | HIGH     | —                                               |
| WS-8  | CI green verification               | HIGH     | —                                               |
| WS-9  | MyPy compliance (14→0)              | MEDIUM   | —                                               |
| WS-10 | Gemini O1/O2/O3                     | LOW      | —                                               |

---

## Quality Gate Compliance

| Gate        | Pre-Sprint                         | Target                |
| :---------- | :--------------------------------- | :-------------------- |
| Ruff        | ✅ 0 errors                        | ✅ 0 errors           |
| ESLint      | ✅ 0 errors                        | ✅ 0 errors           |
| TSC         | ✅ 0 errors                        | ✅ 0 errors           |
| Web Build   | ✅ 38 routes                       | ✅ 38+ routes         |
| MyPy        | ⚠️ `continue-on-error` (14 errors) | ✅ 0 errors, blocking |
| CI Pipeline | ⚠️ VR failing                      | ✅ All 4 jobs green   |

---

## Architectural Decisions

| Decision                                | Rationale                                                                                |
| :-------------------------------------- | :--------------------------------------------------------------------------------------- |
| Two parallel pricing CSS systems        | Landing page and billing page serve different purposes — marketing vs billing-integrated |
| Defensive auth mocking                  | JWT exp=2286 prevents 401, but mock `/api/v1/auth/refresh` for robustness                |
| `billing_enabled: true` in VR mock      | Ensures VR screenshots show actual pricing cards, not "Coming Soon" degraded state       |
| Growth vector uses existing service     | `generate_full_profile` auto-gathers data — worker delegates, doesn't reimplement        |
| CSP conditional on `isDev`              | No dev URLs leak to production CSP headers                                               |
| Mock shape matches TypeScript interface | `FeatureAccessResponse: { tier, engines, scan_limit, billing_enabled }`                  |
