# PathForge — Production Readiness Roadmap

> **Status**: Sprint 23 complete | **Date**: 2026-02-24
> **Goal**: Map what's built, what's missing, and what sprints remain to launch

---

## What's Built (Sprints 1–23)

### Backend API — Production-Grade ✅

| Domain                   | Details                                                                                                                                                                        |
| :----------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Intelligence Engines** | 12 proprietary engines (Career DNA, Threat Radar, Skill Decay, Salary, Simulation, Interview, Hidden Job Market, Passport, Collective, Predictive, Recommendations, Workflows) |
| **API Endpoints**        | 156 REST endpoints across 28 route files                                                                                                                                       |
| **Data Models**          | 66 SQLAlchemy models, 22 Alembic migrations                                                                                                                                    |
| **Test Suite**           | 1,016 tests (unit + integration), all passing                                                                                                                                  |
| **Security**             | JWT auth, rate limiting, OWASP LLM01 guards, prompt sanitization, 0 CVEs                                                                                                       |
| **Observability**        | AI Transparency layer, LLM confidence scoring, TransparencyLog                                                                                                                 |
| **Orchestration**        | Career Command Center™, Notification Engine, GDPR Export                                                                                                                       |

### Web App — Marketing + Shell Dashboard

| Layer              | Details                                                                                               |
| :----------------- | :---------------------------------------------------------------------------------------------------- |
| **Marketing site** | 10 pages (landing, about, features, process, contact, pricing, legal pages)                           |
| **Auth**           | Login + Register routes (UI exists)                                                                   |
| **Dashboard**      | Shell layout + 6 placeholder routes (analytics, applications, matches, onboarding, resumes, settings) |

### Infrastructure

| Component       | Status                                                 |
| :-------------- | :----------------------------------------------------- |
| **CI Pipeline** | `ci.yml` — path-filtered lint, type-check, test, build |
| **Hosting**     | Railway (API) + Vercel (Web) — configured & deployed   |
| **Docker**      | 3 Dockerfiles + compose for local dev                  |
| **Email**       | Resend integration, SPF/DKIM/DMARC verified            |
| **Domain**      | pathforge.eu live with DNS configured                  |
| **Analytics**   | GA4 + Consent Mode v2                                  |
| **Security**    | Turnstile CAPTCHA, security headers, `.well-known`     |

---

## What's Missing for Production Launch

### 🔴 Critical (Must Have)

| #   | Gap                                       | Why Critical                                                                     |
| :-- | :---------------------------------------- | :------------------------------------------------------------------------------- |
| 1   | **Dashboard UI for Intelligence Engines** | 12 engines exist in API but have zero frontend — users can't access them         |
| 2   | **API ↔ Frontend Integration**            | No API client layer, no auth context, no data fetching hooks                     |
| 3   | **Real Database Connection**              | API tests use SQLite; production needs PostgreSQL + pgvector on Supabase/Railway |
| 4   | **Resume Upload & Parsing**               | Core user flow (upload CV → Career DNA) has no UI                                |
| 5   | **Onboarding Flow**                       | Registration → resume upload → Career DNA generation — no connected flow         |

### 🟡 Important (Should Have Before Launch)

| #   | Gap                                   | Why Important                                                  |
| :-- | :------------------------------------ | :------------------------------------------------------------- |
| 6   | **E2E Tests**                         | 1,016 unit/integration tests but zero end-to-end browser tests |
| 7   | **Error Monitoring**                  | No Sentry or equivalent — production errors go silent          |
| 8   | **APM / Metrics**                     | No application performance monitoring beyond health endpoint   |
| 9   | **CD Pipeline**                       | No `deploy.yml` — deployment is manual                         |
| 10  | **Database Migrations in CI**         | Alembic migrations not tested in CI pipeline                   |
| 11  | **Seed Data / Demo Mode**             | No way to demo the product without real LLM calls              |
| 12  | **Loading States & Error Boundaries** | Dashboard needs skeleton loaders, error recovery               |

### 🟢 Nice to Have (Post-Launch)

| #   | Gap                       | Notes                                                     |
| :-- | :------------------------ | :-------------------------------------------------------- |
| 13  | **Mobile App**            | Expo/React Native — deferred from Sprint 7                |
| 14  | **Langfuse Integration**  | LLM observability — config exists but not wired           |
| 15  | **Real Job Aggregation**  | Adzuna/Jooble pipelines built but not running on schedule |
| 16  | **Notification Delivery** | Email digest engine built, needs Resend integration test  |
| 17  | **Admin Dashboard**       | User management, system health, usage analytics           |
| 18  | **Stripe Billing**        | Pricing page exists but no payment integration            |

---

## Proposed Remaining Phases & Sprints

### Phase E: Integration Layer (2 sprints)

> Connect the backend engines to the frontend. No new features — pure wiring.

#### Sprint 24 — API Client & Auth Integration

- TypeScript API client with typed endpoints
- Auth context provider (JWT token management, refresh, logout)
- Protected route middleware
- API error handling and retry logic
- React Query (TanStack Query) data fetching hooks
- Backend health check integration in dashboard shell

#### Sprint 25 — Core User Flow

- Resume upload UI + file handling
- Resume parsing trigger + progress state
- Career DNA generation flow
- Onboarding wizard (register → upload → generate DNA → dashboard)
- User settings/profile connected to API

---

### Phase F: Dashboard UI (3 sprints)

> Build the intelligence dashboard. This is where PathForge's 12 engines become user-facing.

#### Sprint 26 — Career DNA + Threat Radar Dashboard

- Career DNA 6-dimension visualization (radar chart or hexagonal)
- Career Resilience Score™ display
- Skill Shield™ Matrix visualization
- Threat/Opportunity alert cards
- Career Moat Score display

#### Sprint 27 — Intelligence Hub

- Skill Decay tracker with freshness indicators
- Salary Intelligence display with skill impact modeling
- Career Simulation "what-if" interface
- Transition Pathways explorer

#### Sprint 28 — Network Intelligence + Command Center

- Hidden Job Market signal feed
- Cross-Border Passport comparison tool
- Interview prep interface
- Career Command Center (unified 12-engine dashboard)
- Notification preferences UI
- Recommendation feed

---

### Phase G: Data Pipeline & Real Connections (1 sprint)

> Wire real data sources and production database.

#### Sprint 29 — Production Data Layer

- PostgreSQL + pgvector setup (Supabase or Railway Postgres)
- Alembic migration CI verification
- Redis production configuration
- Job aggregation scheduled worker (Adzuna/Jooble cron)
- LiteLLM production model routing verification
- Langfuse LLM observability activation

---

### Phase H: Production Hardening (1 sprint)

> Make it reliable, observable, and deployable without manual steps.

#### Sprint 30 — Reliability & Observability

- Sentry error tracking (API + Web)
- CD pipeline (`deploy.yml` — auto-deploy on merge to production)
- Health check dashboard (uptime, DB, Redis, LLM provider status)
- Structured JSON logging for Railway
- E2E test suite (Playwright — auth, upload, DNA generation, dashboard)
- Performance baseline (Lighthouse, API response time benchmarks)
- Rate limiting with Redis backing (replace in-memory)

---

### Phase I: Mobile (2 sprints, optional pre-launch)

> React Native + Expo — cross-platform mobile app.

#### Sprint 31 — Mobile Foundation

- Expo Router setup, auth flow, API client
- Resume upload from mobile (camera + file picker)
- Career DNA view

#### Sprint 32 — Mobile Intelligence

- Dashboard with engine summaries
- Push notifications (Expo Notifications)
- Offline-first patterns for Career DNA cache

---

### Phase J: Growth & Monetization (2 sprints, post-launch)

#### Sprint 33 — Billing & Access Control

- Stripe integration (subscription tiers)
- Feature gating by plan tier
- Usage metering for AI calls
- Invoice/receipt emails

#### Sprint 34 — Growth Features

- Admin dashboard
- Waitlist → onboarding conversion flow
- Referral system
- Public career profiles (opt-in)

---

## Sprint Summary Table

| Phase | Sprint | Focus                                     | Priority       |
| :---- | :----- | :---------------------------------------- | :------------- |
| **E** | 24     | API Client & Auth Integration             | 🔴 Critical    |
| **E** | 25     | Core User Flow (Resume → DNA → Dashboard) | 🔴 Critical    |
| **F** | 26     | Career DNA + Threat Radar Dashboard       | 🔴 Critical    |
| **F** | 27     | Intelligence Hub UI                       | 🔴 Critical    |
| **F** | 28     | Network Intelligence + Command Center     | 🔴 Critical    |
| **G** | 29     | Production Data Layer                     | 🔴 Critical    |
| **H** | 30     | Reliability & Observability               | 🟡 Important   |
| **I** | 31     | Mobile Foundation                         | 🟢 Optional    |
| **I** | 32     | Mobile Intelligence                       | 🟢 Optional    |
| **J** | 33     | Billing & Access Control                  | 🟡 Post-launch |
| **J** | 34     | Growth Features                           | 🟢 Post-launch |

---

## Minimum Viable Launch = Sprints 24–30

**7 sprints** to go from "marketing site + API backend" to "production-ready SaaS" with:

- ✅ Connected auth flow
- ✅ Resume upload → Career DNA generation
- ✅ Full intelligence dashboard (12 engines)
- ✅ Real database + data pipeline
- ✅ Error monitoring + CI/CD
- ✅ E2E tests

**Estimated effort**: ~14–21 sessions (based on Sprint 1–23 velocity average of 1.5 sessions/sprint)

> [!IMPORTANT]
> Sprints 24–25 (Phase E) are the highest priority. Without API client integration, the 12 engines we built are unreachable by users. Everything else depends on these two sprints.
