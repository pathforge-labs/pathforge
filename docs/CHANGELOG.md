# Changelog

All notable changes to PathForge, organized by sprint.
Format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [Pre-Sprint 40 Session 2] — Auth E2E Tests & Sprint 34 DB Fix — 2026-03-18

### Added

- **Auth E2E test suite** — 4 new Playwright spec files (15 tests total):
  - `email-verification.spec.ts` (5) — verification flow, valid/expired/invalid tokens, resend
  - `logout.spec.ts` (4) — button visibility, redirect, token clearing, nav update
  - `password-recovery.spec.ts` (6) — forgot flow, reset flow, weak password, expired/invalid tokens, resend
  - `fixtures/auth.ts` — shared authenticated page fixture with localStorage token injection
- **Test user seed script** — `testuser@pathforge.dev` / `TestPass123!` with `is_verified=true`

### Fixed

- **Sprint 34 subscriptions table** — applied `subscriptions` table + `role` column via direct SQL (Alembic migration `b2c3d4e5f6g7` was on a dead branch not reachable from head `d4e5f6g7h8i9`)
- **`/users/me` 500 error** — root cause: `get_current_user` dependency uses `selectinload(User.subscription)` which failed when `subscriptions` table was missing
- **`auth.spec.ts`** — fixed display test, empty validation test, and login negative tests
- **`dashboard.spec.ts`** — fixed console errors test

### Changed

- `email-verification.spec.ts` — `Promise.all` with `waitForResponse` pattern to prevent route/navigation race conditions
- `ROADMAP.md` — updated Last Updated, ad-hoc work log, velocity row
- `session-context.md` / `session-state.json` — updated with session work

---

## [Pre-Sprint 40] — Antigravity AI Kit v3.1.0 Upgrade — 2026-03-15

### Added

- **2 new agents**: `reliability-engineer` (SRE, production readiness), `sprint-orchestrator` (sprint planning, velocity)
- **2 new skills**: `context-budget` (LLM token optimization), `mcp-integration` (MCP patterns)
- **5 new directories**: `engine/` (6 runtime modules), `contexts/` (5 behavioral modes), `decisions/` (1 ADR), `templates/` (3 templates), `hooks/` (hooks.json + templates)
- **`manifest.json`** — complete capability registry (19 agents, 31 skills, 31 commands, 15 workflows)
- **`CheatSheet.md`** — 8.6KB full command/workflow/agent reference

### Changed

- **`backend-specialist.md`** — 3.1→8.7KB: multi-ecosystem (Node.js + Python), Decision Frameworks, anti-patterns
- **`frontend-specialist.md`** — 2.6→13KB: Deep Design Thinking, SaaS Safe Harbor, Maestro Auditor
- **`rules/`** — 4→8 files: kit adds `documentation.md`, `sprint-tracking.md`; PF preserves `architecture.md`, `quality-gate.md`
- **`checklists/`** — Sprint State Validation + Staleness check (session-start), Sprint State Sync + Duplicate prevention (session-end)
- **`rules.md`** — 14.4KB comprehensive Trust-Grade governance rules

### Verified

- Pytest: 1103/1103 ✅ | Ruff: 0 ✅ | ESLint: 0 ✅ | TSC: 0 ✅ | Build: 15 routes ✅
- npm audit: 0 vulnerabilities ✅
- 8 PathForge customizations preserved (plan, review, status, migrate, architecture, quality-gate, session files)
- Commit: `a9ae4f3`

---

## [Post-Sprint 37] — CI Stability, Migration Chain & Deprecation Fixes — 2026-03-04

### Fixed

- **Alembic migration chain** — `4d5e6f7g8h9i` `down_revision` pointed to non-existent `6a7b8c9d0e1f`, corrected to `3c4d5e6f7g8h` (interview intelligence tables)
- **`datetime.utcnow()` deprecation** (3 models) — `interview_intelligence.py`, `hidden_job_market.py`, `career_simulation.py` updated to `datetime.now(tz=UTC)` with `UTC` imports
- **`HTTP_422_UNPROCESSABLE_ENTITY` deprecation** (9 instances across 4 files) — replaced with `HTTP_422_UNPROCESSABLE_CONTENT` in `error_handlers.py`, `public_profiles.py`, `career_dna.py`, `career_action_planner.py`

### Changed

- **bcrypt test optimization** — 4 rounds in testing mode (`ENVIRONMENT=testing`) vs 12 in production (~60x faster hashing per call)
- **pytest warning filters** — `slowapi` and `pytest-asyncio` deprecation warnings suppressed via `filterwarnings` in `pyproject.toml`
- **`timeout_method = "thread"`** — explicit Windows-compatible timeout method for `pytest-timeout`
- **CI job timeouts** — all 5 CI jobs now have `timeout-minutes` set
- **`pytest-timeout`** — per-test 120s timeout added to `pyproject.toml`
- **uv migration** — API quality job uses `astral-sh/setup-uv@v7` for 10-100x faster dependency installation

### Verified

- 1,087 passed, **0 warnings** in 575.29s
- Ruff: 0 errors
- 4 commits: `402d67d`, `da580f6`, `5a54c73`, `385ca01`

---

## [Sprint 36 CI Fixes] — Mypy & CI Pipeline Remediation — 2026-03-03

### Fixed

- **Mypy `type-arg` errors** — `dict` → `dict[str, Any]` in `user_activity.py` (details field), `threat_radar.py` (return type + data_points), `career_dna.py` (payload parameter)
- **Worker `attr-defined` error** — stubbed `CareerDNAService.recalculate_growth_vector` (not yet implemented) with warning log in `worker.py`
- **CI migration path** — removed incorrect `working-directory: apps/api` from migration SQL validation step in `ci.yml` (script at repo root uses internal `API_DIR`)

### Production Audit Findings (Sprint 37 Backlog)

- **C1**: Pricing page missing BEM CSS (`pricing-card__*` classes have zero matching styles)
- **C2**: Visual regression auth mismatch (`/api/v1/auth/me` not mocked → dashboard never renders)
- **M1**: Pricing page title duplication (`"Pricing | PathForge | PathForge"`)
- **M2**: CSP `connect-src` missing `localhost:8000` for dev

---

## [Sprint 33] — Testing + Migrations + Security Hardening — 2026-03-02

### Added

- **Alembic merge migration** (`9i0j1k2l3m4n`) — consolidates 4 unmerged heads into single head, creates `push_tokens` table, adds `push_notifications` column to `notif_preferences`
- **Deep link router** (`apps/mobile/lib/deep-link-router.ts`) — whitelist-based route validation with `resolveDeepLink()`, `isValidDeepLink()`, safe fallback to home
- **Code extractions** — `buildDimensions` + `DimensionCard` → `career-dna-helpers.ts`, `getRiskColor`/`getRiskLabel` exported from `threat-summary.tsx`
- **24 new mobile tests** across 4 suites:
  - `build-dimensions.test.ts` (6): profile states, edge cases, dimension mapping
  - `threat-summary.test.tsx` (5): risk thresholds, color/label mapping
  - `use-push-notifications.test.ts` (6): permission flow, registration, deregistration, error handling
  - `deep-link-router.test.ts` (7): known routes, fallback, validation, security

### Changed

- **`push_service.py`** — `deregister_token()` now requires `user_id` parameter for ownership verification
- **`notifications.py`** — passes `current_user.id` to `deregister_token` service method
- **`notifications.ts` (mobile API client)** — `deregisterPushToken()` sends token via `RequestOptions.body`
- **`use-push-notifications.ts`** — integrated `resolveDeepLink()` for validated deep link navigation; sends `expoPushToken` on deregister
- **`career-dna.tsx`** — imports `buildDimensions` and `DimensionCard` from extracted helper module
- **`package.json` (web)** — pinned `@types/react` to `19.2.14` and `@types/react-dom` to `19.2.3` (removed caret ranges)

### Security

- **F2 (Critical)**: Ownership verification on push token deregistration — prevents any user from deregistering another user's token
- **F3 (High)**: Client-server contract mismatch fixed — mobile now sends token in request body as expected by server
- **F6 (Medium)**: PII masking — `mask_token()` hides all but last 4 chars of device tokens in API responses (`get_status`, `register_push_token`)
- **7 Dependabot alerts resolved** — pnpm overrides for `tar@>=7.5.8` (CVE-2026-26960, -24842, -23950, -23745), `serialize-javascript@>=7.0.3` (GHSA-5c6j), `minimatch@>=10.2.3` (CVE-2026-27903, -27904)
- `pnpm audit`: **0 known vulnerabilities**

### Added (Session 2)

- **F4: Rate limit redesign** — dispatch-based counter (`daily_push_count`, `last_push_date` columns on `NotificationPreference`), `_get_daily_push_count()` pure function, `_increment_dispatch_count()` helper, `rate_limit_push` config (10/min)
- **F7: Connection pooling** — shared `httpx.AsyncClient` singleton (`get_http_client()`, `close_http_client()`), configured with `max_connections=10`, `max_keepalive=5`, lifespan shutdown hook
- **Alembic migration** `a1b2c3d4e5f6` — `daily_push_count` (Integer, default 0) + `last_push_date` (Date, nullable) on `notif_preferences`
- **14 new backend tests** (`test_push_service.py`) — F4 counter logic (5), F6 masking (6), F7 client lifecycle (3)

---

## [Sprint 29] — Production Data Layer — 2026-02-27

### Added

- **Circuit Breaker** (`app/core/circuit_breaker.py`) — Redis-backed async context manager for external API resilience (CLOSED→OPEN→HALF_OPEN states, auto-expiry, recovery probes)
- **PII Redactor** (`app/core/pii_redactor.py`) — 7 high-confidence regex patterns (email, phone, SSN, BSN, CC, IP, URL tokens). Name detection deliberately excluded (40% precision — policy decision, not gap)
- **Document Parser** (`app/services/document_parser.py`) — secure PDF/DOCX/TXT parser: 10MB size limit, 100-page memory guard, MIME verification via `filetype`, encrypted PDF rejection, macro-enabled DOCX rejection, `asyncio.to_thread` sandboxing
- **Alembic CI Scripts** — `scripts/alembic_verify.py` (upgrade→downgrade→re-upgrade→drift check, Alembic ≥1.13.0 assertion) + `scripts/alembic_dry_run.py` (SQL preview). Python-based for Windows compatibility
- **LLM Budget Counter** — Redis-backed monthly spend tracking (`pathforge:llm_cost:YYYY-MM`), `BudgetExceededError` fail-fast, automatic 40-day TTL cleanup
- **LLM RPM Guards** — in-memory 60-second sliding window per tier, `RateLimitExceededError`
- **Langfuse PII Redaction Hook** — `litellm.input_callback` pre-call hook scrubs messages before Langfuse trace export
- **Alembic drift check** step added to GitHub Actions `ci.yml`
- 3 new AI optional deps: `pdfplumber>=0.11.0`, `python-docx>=1.1.0`, `filetype>=1.2.0`

### Changed

- **`config.py`** — `EMBEDDING_DIM = 3072` module constant + 14 production settings (DB pool, Redis SSL, LLM budget/RPM, Langfuse sampling/PII, aggregation cron/batch/daily limit)
- **`database.py`** — SSL context builder for Supabase, `pool_recycle`, `pool_timeout` from config
- **`resume.py` / `matching.py`** — `Vector(3072)` → `Vector(EMBEDDING_DIM)` (audit C2)
- **`rate_limit.py`** — **CRITICAL FIX**: `storage_uri` now reads from `settings.ratelimit_storage_uri` instead of hardcoded `memory://` (audit C1 — multi-instance bypass)
- **`worker.py`** — Redis SSL + `conn_timeout` for ARQ connection
- **`llm.py`** — budget check before every LLM call, RPM check per tier, cost recording after success
- **`llm_observability.py`** — `LANGFUSE_SAMPLE_RATE` env var (10% default), PII redaction hook registration, enhanced startup logging
- **`initial_schema.py`** — `CREATE EXTENSION IF NOT EXISTS vector` (pgvector safety net)

### Security

- 0 npm vulnerabilities (audit --audit-level=moderate)
- PII redacted before Langfuse export
- Input validation: file size, page count, MIME, encrypted PDF blocked
- All credentials via environment variables

---

## [Sprint 25] — Core User Flow — 2026-02-26

### Added

- **FileUpload component** (`components/file-upload.tsx`) — drag-drop + click-to-browse, 5MB limit, `.txt/.pdf/.doc/.docx` accept, accessibility (keyboard, ARIA), file preview with size formatting
- **Career DNA Readiness Score™** (`components/career-dna-readiness.tsx`) — animated SVG circular progress ring (0–100), 6-dimension status grid, score-tier coloring, contextual guidance. **Innovation: no competitor offers this.**
- **User Profile hooks** (`hooks/api/use-user-profile.ts`) — `useUserProfile`, `useOnboardingStatus` (auth-gated queries), `useUpdateProfile`, `useRequestDataExport` (mutations with invalidation)
- **23 new frontend tests** across 3 suites:
  - `use-user-profile.test.ts` (7): auth-gating, mutations, query invalidation
  - `file-upload.test.tsx` (8): validation, callbacks, error states, file removal
  - `use-onboarding.test.ts` (8): state machine, navigation constraints, reset
- Architecture decision record: `docs/architecture/sprint-25-core-user-flow.md` with 12-competitor analysis
- 12-competitor market analysis confirming PathForge as first-mover in individual-owned career intelligence

### Changed

- **Onboarding hook** (`hooks/use-onboarding.ts`) — upgraded from 4→5 steps (upload→parse→dna→readiness→dashboard), added `file` state + `setFile()`, `generateCareerDna()`, FileReader support for `.txt`
- **Onboarding page** (`onboarding/page.tsx`) — full rewrite: FileUpload + paste toggle, parse preview, Career DNA generation progress, Readiness Score™ display, dashboard redirect
- **Dashboard page** (`dashboard/page.tsx`) — dynamic data from `useCareerDnaSummary`, `useOnboardingStatus`, skeleton loaders, conditional Get Started CTA, `bg-linear-to-br` (Tailwind v4)
- **Settings page** (`settings/page.tsx`) — profile CRUD with inline edit form, GDPR data export request (Art. 20), error/success feedback
- `ROADMAP.md` — Sprint 25 marked complete with implementation detail
- `session-context.md` / `session-state.json` — updated with Sprint 25 metrics

---

## [Sprint 24] — API Client & Auth Integration (Remediation + Tests) — 2026-02-25

### Added

- **Vitest test infrastructure** — greenfield setup for frontend API client layer:
  - `vitest.config.mts` — happy-dom environment, `@/` path aliases, Tier-1 coverage thresholds (80/75/80/80)
  - `__tests__/test-helpers.ts` — shared fetch/localStorage mock utilities + response builders
  - 3 npm scripts: `test`, `test:watch`, `test:coverage`
- **60 unit tests across 5 suites** — comprehensive API client coverage:
  - `http.test.ts` (20): auth headers, 401 refresh flow, error parsing, AbortController, convenience methods
  - `token-manager.test.ts` (9): storage ops, state queries, listener notifications, error resilience
  - `refresh-queue.test.ts` (7): single-flight queueing, concurrent resolution, failure propagation
  - `auth.test.ts` (4): login, register, refresh, logout endpoint verification
  - `domains.test.ts` (20): AI, Applications, Analytics, Blacklist, Health, Users
- **16 hook tests** (`hooks.test.ts`) — TanStack Query hook validation:
  - Auth-gating (disabled when unauthenticated), query delegation, mutation triggers + cache invalidation
  - All 4 hook files: useHealth, useCareerDna, useCommandCenter, useNotifications
- **22 provider tests** — AuthProvider + QueryProvider:
  - `auth-provider.test.ts` (18): 7 reducer pure-function + 10 integration (session, login, register, logout, multi-tab) + 1 useAuth guard
  - `query-provider.test.ts` (4): 4xx retry skip, mutation no-retry, window focus disabled

### Changed

- **R1: Legacy API migration** — 10 consumer files migrated from `lib/api.ts` → `lib/api-client/` domain modules
- **R2: AbortController support** — optional `signal` property on `RequestOptions`, forwarded to native `fetch`
- **O1: CI test gate** — `pnpm test` step added to `web-quality` job in `ci.yml` (lint → test → build)
- `package.json` — Vitest, `@vitest/coverage-v8`, `happy-dom`, `@testing-library/react`, `@testing-library/dom` added as devDependencies

### Removed

- `lib/api.ts` — legacy monolith API client (superseded by domain-split `lib/api-client/`)

---

## [Sprint 23] — Delivery Layer — 2026-02-24

### Added

- **Cross-Engine Recommendation Intelligence™** — multi-engine fusion pipeline:
  - Priority-Weighted Score™ algorithm: urgency(0.40) × impact(0.35) × inverse_effort(0.25)
  - Cross-Engine Correlation Map™ with per-recommendation engine attribution
  - Confidence cap at 0.85 (CheckConstraint enforced) — prevents AI overconfidence
  - 4 SQLAlchemy models + 3 StrEnums, 8 response + 3 request schemas, 9 REST endpoints
  - 6 recommendation template types with ENGINE_DISPLAY_NAMES for 12 engines
- **Career Workflow Automation Engine™** — smart career workflow system:
  - 5 Smart Workflow Templates™: Skill Acceleration, Threat Response, Opportunity Capture, Salary Negotiation, Career Review
  - Trigger-based activation (engine_change, vitals_threshold, scheduled, manual)
  - Step-level tracking with auto-complete logic and WorkflowExecution audit trail
  - 4 SQLAlchemy models + 3 StrEnums, 7 response + 4 request schemas, 10 REST endpoints
- 115 Sprint 23 tests (80 unit + 35 integration) — 1,016/1,016 total passing

### Changed

- `main.py` — 2 new routers registered at `/api/v1`
- `models/__init__.py` — 8 new models imported + `__all__` expanded

### Fixed

- **R1**: Alembic migration `0c2d3e4f5g6h` — 8 tables for Delivery Layer (4 RI + 4 WF)
- **pip CVE-2026-1703**: Upgraded pip 25.2 → 26.0.1 (executable injection fix)
- **cryptography CVE-2026-26007**: Upgraded 46.0.4 → 46.0.5
- **ecdsa CVE-2024-23342**: Migrated `python-jose` → `PyJWT 2.11.0` (eliminates transitive ecdsa dependency)

---

## [Sprint 22] — Career Orchestration Layer — 2026-02-24

### Added

- **Unified Career Command Center™** — 12-engine orchestration dashboard:
  - Career Vitals™ weighted composite score (0-100, 85% confidence cap)
  - Engine Heartbeat™ 4-tier classification + trend detection
  - 3 SQLAlchemy models + 5 StrEnums, 10+ Pydantic schemas, 8 REST endpoints
- **Notification Engine™** — event-driven career notifications:
  - Severity tiers, digest scheduling, quiet hours, preference-based suppression
  - 2 SQLAlchemy models + 3 StrEnums, 10+ Pydantic schemas, 8 REST endpoints
- **User Profile & GDPR Data Export** — Article 20+ compliant:
  - Export pipeline with AI methodology disclosure + SHA-256 checksums
  - 1-export-per-24h rate limiting, onboarding status tracking
  - 2 SQLAlchemy models + 3 StrEnums, 10+ Pydantic schemas, 7 REST endpoints
- Alembic migration `0b1c2d3e4f5g` — 7 tables with FK CASCADE + indexes + CHECK constraints
- 101 Sprint 22 tests: 39 CCC + 35 Notification + 27 Profile (901/901 total passing)
- SQLite UUID compatibility fix in `conftest.py` (DDL compiler + bind/result processors)

### Changed

- `main.py` — 3 new routers registered at `/api/v1`
- `models/__init__.py` — 7 new models + `__all__` sort fix
- `conftest.py` — UUID type compatibility for PostgreSQL ↔ SQLite test environments

### Fixed (Audit Remediation — 2026-02-24)

- **MyPy career_action_planner** — `ComparePlansResult.recommended_plan_id` type `str | None` → `uuid.UUID | None`, `model_validate()` replaces `**dict` spread, direct import from helpers module
- **conftest.py TYPE_CHECKING** — `TYPE_CHECKING` guard for `User`, `from __future__ import annotations`, typed all compiler functions + fixtures, narrowed `type: ignore[method-assign]`
- **Async export queue** — `request_export` now returns `"processing"` immediately via `asyncio.create_task`, 50MB `MAX_EXPORT_SIZE_BYTES` OOM guard, compact JSON serialization
- **Email digest delivery** — Resend API integration with config-gated `_send_digest_email`, `sent_at` column on `NotificationDigest`, `_format_digest_html` branded template
- Updated `test_user_profile.py` assertion for async export response format

---

## [Sprint 21] — Career Action Planner™ — 2026-02-23

### Added

- **Career Action Planner™** — time-boxed career development planning system:
  - 5 SQLAlchemy models + 4 StrEnums, 14 Pydantic schemas
  - 4 LLM methods (priorities, milestones, progress evaluation, recommendations) + 4 clamping validators
  - CareerActionPlannerService pipeline (~718 lines) + helper module (218 lines)
  - 3 typed pipeline DTOs: `DashboardResult`, `GeneratePlanResult`, `ComparePlansResult`
  - 10 REST endpoints at `/api/v1/career-action-planner`
  - Alembic migration `0a1b2c3d4e5g` — 5 tables
  - 73 unit tests + 12 mocked LLM integration tests (800/800 total passing)
- **Career Sprint Methodology™** — time-boxed career development cycles
- **Intelligence-to-Action Bridge™** — converts intelligence engine outputs → actionable milestones
- **Adaptive Plan Recalculation™** — dynamic re-prioritization based on progress + new intelligence
- Security scanning tools: `bandit` + `pip-audit` installed in dev environment

### Changed

- `career_action_planner_service.py` — extracted 4 helpers + `compare_plans` to `_career_action_planner_helpers.py` (896 → 718 lines)
- `career_action_planner.py` (API routes) — 3 endpoints updated to use typed DTO attribute access
- `main.py` — `career_action_planner.router` wired at `/api/v1`

---

## [Sprint 20] — AI Trust Layer™ — 2026-02-23

### Added

- **AI Trust Layer™** — user-facing AI transparency infrastructure for explainability:
  - `TransparencyRecord` dataclass with 12 fields (ID, type, model, confidence, sources, tokens, latency)
  - `TransparencyLog` thread-safe per-user circular buffer (200 records/user, 1000 users max)
  - `compute_confidence_score()` — 4-signal algorithm (tier, retries, latency, token utilization), capped at 95%
  - 2 LLM wrappers: `complete_with_transparency()`, `complete_json_with_transparency()`
  - 3 Pydantic v2 schemas: `AIAnalysisTransparencyResponse`, `RecentAnalysesResponse`, `AIHealthResponse`
  - 3 REST endpoints at `/api/v1/ai-transparency` (public health dashboard, auth-gated analyses list + detail)
  - User isolation: 404 for other users' analyses, auth-gated endpoints
- **Career DNA Service Integration (PoC)** — transparency logging wired into production pipeline:
  - All 5 LLM-calling analyzer methods return `tuple[data, TransparencyRecord | None]`
  - `_log_transparency()` helper logs records to per-user TransparencyLog
  - 4 `_compute_*` service helpers pass `user_id` through orchestration chain
  - Analysis types: `career_dna.hidden_skills`, `.experience_blueprint`, `.growth_vector`, `.values_profile`, `.summary`
- 44 new tests: 33 unit, 8 API, 3 integration (717/717 total passing)
- Market-first: no competitor exposes per-analysis confidence + data sources to end users

### Changed

- `career_dna_analyzer.py` — all 5 LLM methods use `complete_json_with_transparency` instead of `complete_json`
- `career_dna_service.py` — all 4 LLM-backed compute helpers accept `user_id` and log TransparencyRecords
- `llm.py` — added transparency wrapper layer maintaining backward compatibility
- `main.py` — `ai_transparency.router` wired at `/api/v1`

---

## [Sprint 19] — Predictive Career Engine™ — 2026-02-23

### Added

- **Predictive Career Engine™** — industry's first individual-facing predictive intelligence system:
  - 5 SQLAlchemy models (`EmergingRole`, `DisruptionForecast`, `OpportunitySurface`, `CareerForecast`, `PredictiveCareerPreference`) + 5 StrEnums
  - 14 Pydantic schemas with `data_source` + `disclaimer` transparency fields
  - Alembic migration `7g8h9i0j1k2l` — 5 tables with FK CASCADE, indexes, `CheckConstraint` (confidence ≤ 0.85)
  - AI analyzer: 4 LLM methods + 2 static helpers + 4 clamping validators, `MAX_PC_CONFIDENCE` 0.85 cap
  - PredictiveCareerService pipeline orchestration (~594 lines)
  - 8 REST endpoints at `/api/v1/predictive-career` (dashboard, scan, 4 analysis, preferences GET/PUT)
  - 71 new tests (673/673 total passing)
- **Emerging Role Radar™** — skill-overlap + trend detection for nascent roles
- **Disruption Forecast Engine™** — per-user severity scoring + mitigation strategies
- **Proactive Opportunity Surfacing** — multi-signal time-sensitive opportunity detection
- **Career Forecast Index™** — composite 4-component weighted score (0-100), no competitor equivalent
- 4 versioned OWASP LLM01-hardened prompt templates (emerging roles, disruption, opportunity, career forecast)
- Architecture reference: `docs/architecture/sprint-19-predictive-career-engine.md`
- Ethics safeguards: confidence cap (0.85), transparency fields, anti-panic prompts, no outcome guarantees

---

## [Sprint 18] — Infrastructure & Auth Integration — 2026-02-22

### Added

- **`app/core/auth.py`** — canonical auth dependency re-export module (`get_current_user`)
- **Rate limiting** on all 9 Collective Intelligence endpoints via `slowapi`:
  - 5× POST analysis endpoints: `settings.rate_limit_career_dna` (3/min)
  - POST `/scan`: `2/minute` (heaviest pipeline)
  - GET `/dashboard`: `settings.rate_limit_embed` (20/min)
  - GET `/preferences`: `settings.rate_limit_parse` (30/min)
  - PUT `/preferences`: `settings.rate_limit_embed` (20/min)
- **Auth-aware integration test fixtures**:
  - `authenticated_user` — direct DB user creation (bypasses HTTP endpoints)
  - `auth_client` — pre-authenticated `AsyncClient` with JWT token
- **`test_auth_integration.py`** — 5 integration tests:
  - Full lifecycle: register → login → protected endpoint → refresh → re-access
  - Fixture validation (`auth_client`, `authenticated_user`)
  - Edge cases: no-token (401), invalid-token (401)

### Fixed

- **168 pre-existing test errors** resolved — `ModuleNotFoundError: app.core.auth` unblocked all integration tests (429→602 total passing)

---

## [Sprint 14] — Interview Intelligence™ — 2026-02-21

### Added

- **Interview Intelligence™** — full interview preparation system:
  - 5 SQLAlchemy models (`InterviewPrep`, `CompanyInsight`, `InterviewQuestion`, `STARExample`, `InterviewPreference`) + 4 StrEnums
  - 14 Pydantic schemas with `ConfigDict(from_attributes=True)` + `data_source` + `disclaimer` transparency fields
  - Alembic migration `3c4d5e6f7g8h` — 5 tables with FK CASCADE, indexes, `CheckConstraint` (confidence ≤ 0.85)
  - AI analyzer: 5 LLM methods + 4 validators, versioned prompt templates
  - InterviewIntelligenceService pipeline orchestration (~680 lines)
  - 11 REST endpoints at `/api/v1/interview-intelligence` (dashboard, prep, compare, preferences, questions, STAR, negotiation)
  - 56 new tests (438/438 total passing)
- **Career DNA Interview Mapper™** — maps Career DNA dimensions to STAR examples
- **Negotiation Script Engine™** — generates salary negotiation strategies with Salary Intelligence cross-integration
- **Company Culture Decoder™** — AI-powered interview culture analysis
- `prep_depth` `Literal` type validation (`quick | standard | comprehensive`)
- Architecture reference archived to `docs/architecture/sprint-14-interview-intelligence.md`

### Changed

- **Transition Pathways DRY refactor** — extracted `_build_scan_response` helper, added `ConfigDict(from_attributes=True)` to 7 schemas, replaced field-by-field mapping with `model_validate()` across 11 routes (−218 lines)
- **Career Simulation DRY refactor** — replaced `_build_full_response` (−52 lines) and preference routes (−10 lines) with `model_validate()`

### Fixed

- **MyPy type overhaul** — resolved all 15 type warnings (15→0) across 6 files:
  - Missing `dict` type parameters in `CompanyInsight.content` and `SimulationOutput.factors`
  - Variable type reuse in service loop variables (4 fixes)
  - `_load_prep_with_relations` param type `str` → `uuid.UUID`
  - `_build_scan_response` param type `object` → `Any`
  - `CareerSimulation` undefined name (added `TYPE_CHECKING` import)
  - `career_dna_id` `str`/`UUID` mismatch (resolved via `model_validate`)

---

## [Sprint 13] — Career Simulation Engine™ — 2026-02-21

### Added

- **Career Simulation Engine™** — full "what-if" career scenario planner:
  - 5 SQLAlchemy models (`CareerSimulation`, `SimulationInput`, `SimulationOutcome`, `SimulationRecommendation`, `SimulationPreference`) + 3 StrEnums
  - 14 Pydantic schemas with `ConfigDict(from_attributes=True)` + `data_source` + `disclaimer` transparency fields
  - Alembic migration `2b3c4d5e6f7g` — 5 tables with FK CASCADE, indexes, `CheckConstraint` (confidence ≤ 0.85)
  - AI analyzer: 4 LLM methods + 4 static helpers + 3 clamping validators
  - CareerSimulationService pipeline orchestration (~600 lines)
  - 11 REST endpoints at `/api/v1/career-simulation` (dashboard, 5 scenario types, comparison, preferences)
  - 52 new tests (382/382 total passing)
- **Career Scenario Simulator™** — scenario-type-specific "what-if" analysis (role, geo, skill, industry, seniority)
- **Scenario Confidence Metric™** — hard-capped at 0.85 with DB-level CHECK constraint
- **ROI Calculator™** — salary impact %, time investment, feasibility scoring
- **Pagination** — `page`/`per_page` query params on dashboard and list endpoints
- Ethics safeguards: confidence cap (0.85), `data_source` + `disclaimer` on every response, anti-overconfidence prompts

### Fixed

- Stale `SimulationStatus` docstring (old enum values → `draft | running | completed | failed`)

---

## [Sprint 12] — Transition Pathways — 2026-02-20

### Added

- **Transition Pathways** — full career transition intelligence system:
  - 5 SQLAlchemy models (`TransitionPath`, `SkillBridgeEntry`, `TransitionMilestone`, `TransitionComparison`, `TransitionPreference`) + 4 StrEnums
  - 15 Pydantic schemas with `data_source` + `disclaimer` transparency fields
  - Alembic migration `1a2b3c4d5e6f` — 5 tables with FK CASCADE + indexes
  - AI analyzer: 4 LLM methods + 4 static helpers, `MAX_TRANSITION_CONFIDENCE` (0.85) cap
  - TransitionPathwaysService pipeline orchestration (~500 lines)
  - 11 REST endpoints at `/api/v1/transition-pathways` (dashboard, explore, what-if, compare, milestones, preferences)
  - 43 new tests (330/330 total passing)
- **Career Velocity Corridor™** — 3-point timeline estimation (optimistic/realistic/conservative)
- **Skill Bridge Matrix™** — per-skill gap analysis with acquisition methods + weekly estimates
- **Transition Timeline Engine™** — 4-phase milestone planning (preparation → establishment)
- Ethics safeguards: confidence cap (0.85), gender-neutral prompts, no demographic assumptions, conservative timeline bias

### Fixed

- Model type annotations: `preferred_industries`/`excluded_roles` corrected from `dict[str, Any]` to `list[str]`
- Schema generic types: bare `dict` → `dict[str, Any]`
- `what_if` endpoint rewritten to call service directly (MyPy `no-any-return` fix)
- 5 ruff lint fixes: unused import, `.keys()` iteration, `__all__` sorting, import ordering

---

## [Sprint 11] — Salary Intelligence Engine™ — 2026-02-20

### Added

- **Salary Intelligence Engine™** — full salary intelligence system:
  - 5 SQLAlchemy models (`SalaryEstimate`, `SkillSalaryImpact`, `SalaryHistoryEntry`, `SalaryScenario`, `SalaryPreference`) + 3 StrEnums
  - 13 Pydantic schemas with `data_source` + `disclaimer` transparency fields
  - Alembic migration `9j0k1l2m3n4o` — 5 tables with FK CASCADE + indexes
  - AI analyzer: 4 LLM methods + 4 static helpers, centralized `MAX_LLM_CONFIDENCE` (0.85) cap
  - SalaryIntelligenceService pipeline orchestration (~540 lines)
  - 10 REST endpoints at `/api/v1/salary-intelligence` (dashboard, scan, estimate, skill-impacts, trajectory, scenarios, preferences)
  - 41 new tests (287/287 total passing)
- **CareerDNA profile context columns** — `primary_industry`, `primary_role`, `location`, `seniority_level` (migration `0a1b2c3d4e5f`)
- **LLM confidence guardrails** — `SALARY_DATA_SOURCE`, `SALARY_DISCLAIMER`, `MAX_LLM_CONFIDENCE` constants for AI transparency
- Ethics safeguards: confidence cap (0.85), "estimates not guarantees" disclaimers, anti-bias prompts

### Fixed

- Service helpers used `getattr` fallback for missing CareerDNA columns → now use direct attribute access
- "Industries" label → "Industry Diversity" in LLM prompt formatting

---

## [Sprint 10] — Skill Decay & Growth Tracker — 2026-02-20

### Added

- **Skill Decay & Growth Tracker** — full decay intelligence system:
  - 5 SQLAlchemy models (`SkillFreshness`, `MarketDemandSnapshot`, `SkillVelocityEntry`, `ReskillingPathway`, `SkillDecayPreference`) + 4 StrEnums
  - 11 Pydantic schemas for request/response validation
  - Alembic migration `8g9h0i1j2k3l` — 5 tables with FK CASCADE + indexes
  - AI analyzer: 4 LLM methods + 4 static math helpers (exponential decay, half-life, urgency)
  - SkillDecayService pipeline orchestration (687 lines)
  - 9 REST endpoints at `/api/v1/skill-decay` (dashboard, scan, freshness, demand, velocity, reskilling, refresh, preferences)
  - 38 new tests (246/246 total passing)
- **Shell conventions skill** — `.agent/skills/shell-conventions/SKILL.md` for PowerShell 5.x compatibility
- 12 workflow/agent `&&` fixes across 6 files

### Fixed

- 4 migration-model alignment issues (column widths, nullability)
- 3 MyPy type errors in `_get_all` generic helper

---

## [Ad-Hoc] — Turnstile CSP Console Fix — 2026-02-19

### Changed

- **Turnstile execution mode** — switched from implicit (challenge on page load) to `execution: 'execute'` (challenge on form submit only)
- **Script loading strategy** — changed from `afterInteractive` to `lazyOnload` for deferred loading
- **Form components** — both `waitlist-form` and `contact-form` now call `execute()` on submit

### Fixed

- **CSP fallback warnings** — eliminated `script-src not explicitly set` console errors
- **Private Access Token 401s** — no longer triggered on idle page load
- **Preload timing warnings** — Cloudflare challenge resources no longer preloaded unnecessarily

---

## [Ad-Hoc] — UI/UX Polish & Testimonials — 2026-02-19

### Added

- **Ali Avci testimonial** — new card with `.webp` photo, cybersecurity/enterprise perspective
- **Testimonial drag-to-scroll** — desktop Pointer Events API with grab cursor, drag threshold, click prevention
- **Testimonial touch swipe** — mobile horizontal gesture detection (doesn't hijack vertical scroll)
- **Testimonial arrow controls** — left/right chevron buttons with brand gradient styling

### Changed

- **Scroll-to-top button** — enlarged to 50×50px, brand gradient bg, white icon, rounded-full
- **Footer copyright** — `"PathForge by PathForge"` → `"PathForge. All rights reserved."`
- **Navbar** — removed gradient pipe divider between theme toggle and CTA
- **PWA theme-color** — moved to `viewport` export with dark/light media queries (Next.js 16)
- **Müslüm Gezgin photo** — updated to clean version (no "Open To Work" banner)

---

## [Ad-Hoc] — Waitlist Duplicate Handling — 2026-02-19

### Added

- **Duplicate detection** — proactive check before Resend contact creation
- **Differentiated emails** — new subscribers get welcome email, returning subscribers get acknowledgment
- **Rate limiting** — IP-based throttle on waitlist endpoint
- **Turnstile CAPTCHA** — bot protection via Cloudflare Turnstile integration

---

## [Ad-Hoc] — Turnstile Error Resolution — 2026-02-19

### Added

- **`useTurnstile` hook** — centralized Turnstile widget lifecycle management
- **Global script loading** — Turnstile script loaded once in marketing layout
- **Dev environment skip** — Turnstile disabled in development to prevent preload warnings

### Fixed

- **Error 300030** — resolved by proper widget cleanup and re-render handling
- **Preload warnings** — eliminated by loading script at layout level
- **Widget hang** — fixed with explicit reset/remove lifecycle in hook

---

## [Ad-Hoc] — Security Hardening & Deploy Optimization — 2026-02-18

### Added

- **API security hardening** — RFC 9116 `security.txt`, `robots.txt`, bot trap middleware, favicon 204 handler
- **BotTrapMiddleware** — 23 exploit paths blocked in production
- **SECURITY.md** — GitHub Security Policy for responsible disclosure
- **Production docs protection** — `/docs`, `/redoc`, `/openapi.json` disabled in production
- 6 new tests (208/208 total passing)

### Changed

- **Pre-push hook** — fast mode default (lint + types only, ~12s vs ~7min)
- **`ci-local.ps1`** — added `-Fast` switch, skips Pytest + Next.js build
- **Production merge detection** — fixed `--no-ff` merge skip (ancestor check direction)
- **LOCAL-CI-GATE.md** — rewritten with Tier-1 Quality Strategy documentation

### Removed

- **`deploy.yml`** — removed redundant GitHub Actions deploy workflow (Railway native integration handles deploys)

### Fixed

- **Railway deploy conflict** — `railway up` CLI blocked by native GitHub integration (403 Forbidden)
- **Security endpoints not deployed** — Railway watchPatterns skipped merge commits, forced rebuild via trigger commit

---

## [Ad-Hoc] — Railway Deploy, DNS & DKIM — 2026-02-18

### Added

- **Railway API deployment** — 3 fixes applied (port binding, watchPatterns, `.[ai]` deps), health check verified
- **Redis service** — added to Railway, `REDIS_URL` + `RATELIMIT_STORAGE_URI` configured
- **DNS configuration** — `pathforge.eu` A record → Vercel, `www` CNAME → Vercel, `api` CNAME → Railway
- **DKIM authentication** — Google Workspace key generated, `google._domainkey` TXT record added, verification active
- **13 Railway env vars** — JWT secrets, DB, Redis, CORS, port configured
- **6 Vercel env vars** — Resend keys, GA4 ID, API URL, Corepack (Production-only)
- **RAILWAY_TOKEN** — generated and added to GitHub Secrets

### Changed

- `Dockerfile.api` — `pip install .` → `pip install ".[ai]"` (litellm/langchain/voyageai)
- `railway.toml` — hardcoded `--port 8000`, expanded `watchPatterns`

---

## [Ad-Hoc] — Production Infrastructure Setup — 2026-02-17

### Added

- **Google Workspace** — `emre@pathforge.eu` with 4 aliases (hello, support, privacy, info)
- **Resend integration** — SPF, DKIM, DMARC DNS records verified, API key configured
- **GA4 analytics** — `G-EKGQR1ZWH3` with Consent Mode v2 implementation
- **Google Search Console** — DNS TXT verification, `robots.ts` with Googlebot rules
- **Vercel deploy pipeline** — monorepo build config, auto-deploy disabled (`exit 0`)
- **GitHub Secrets** — `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID`, `VERCEL_TOKEN` configured
- **Vercel project** linked via CLI (`.vercel/project.json`)

### Fixed

- **pnpm version conflict** — removed explicit `version: 10` from `pnpm/action-setup` in `deploy.yml` and `ci.yml` (conflicts with `packageManager` field in `package.json`)

### Changed

- Root `package.json` — added `packageManager: "pnpm@10.28.2"` for Vercel Corepack
- Vercel production branch set to `production`, Node.js version set to `22.x`

---

## [Ad-Hoc] — Contact Page Redesign & Navigation — 2026-02-16

### Added

- **Contact page redesign** — premium Tier-1 2-column layout inspired by BeSync:
  - Department cards (General Inquiries, Business & Press with COMING SOON badge, Location)
  - Subject `<select>` dropdown with ChevronDown indicator (6 categories)
  - 2×2 FAQ grid, enhanced social cards with brand-color hover effects
  - Ambient radial gradient blobs, glassmorphism card styling
  - Response time trust badge (24–48 hours), GDPR + data safety badges
- **Contact API route** — `POST /api/contact` with Resend email, XSS prevention, rate limiting, subject allowlist validation
- **Navigation updates** — Contact link added to navbar, mobile nav, and footer
- `/contact` added to `sitemap.ts` and JSON-LD breadcrumbs
- `brand.ts` updated with social links (`linkedin`, `instagram`, `x`) and company constants

### Changed

- Removed "Sign In" from navbar (pre-launch)
- Frontend form inputs now include `maxLength` to match backend validation limits

---

## [Ad-Hoc] — MyPy Type Safety & CI Fix — 2026-02-16

### Fixed

- **MyPy type overhaul**: Resolved all 165 type errors → 0 across 69 source files (32 files modified)
  - Generic type parameterization (`dict` → `dict[str, Any]`, `list` → `list[Any]`)
  - Forward reference handling (`TYPE_CHECKING` + `from __future__ import annotations`)
  - 3 real bugs discovered: missing `user_id` args in `ResumeService.get_by_id` calls
  - 2 test mock fixes: `uselist=False` relationship patterns
  - `CareerDNAChildModel` TypeAlias for type-safe generic helpers
  - `AlertPreference` model fields aligned: `dict[str, Any]` → `list[str]`
- **CI pipeline**: Added `.[ai]` extras to `pip install` in `ci.yml` — resolved `voyageai`/`litellm` test collection failures
- **LOCAL-CI-GATE.md**: Updated output example, design decisions, setup instructions

---

## [Sprint 9] — Career Threat Radar™ — 2026-02-15

### Added

- **Career Threat Radar™** — full threat intelligence system:
  - 6 SQLAlchemy models (`AutomationRisk`, `IndustryTrend`, `SkillShieldEntry`, `CareerResilienceSnapshot`, `ThreatAlert`, `AlertPreference`) + 7 StrEnums
  - 14 Pydantic schemas for request/response validation
  - Alembic migration `7f8g9h0i1j2k` — 6 tables with FK CASCADE + indexes
  - ONET Frey-Osborne dataset (130 SOC codes, 20 categories) + cached data loader
  - AI analyzer: 4 LLM methods with versioned prompt templates
  - Signal Fusion Engine: CRS™ (5-factor composite) + Career Moat Score (4-dimension)
  - 10 REST endpoints at `/api/v1/threat-radar`
  - 25 new tests (202/202 total passing)
- **Ethics safeguards**: confidence cap (0.85), HIGH alert evidence gate (≥2 sources), mandatory Threat→Opportunity pairing, anti-catastrophizing prompts

---

## [Sprint 8] — Career DNA Activation — 2026-02-15

### Added

- **Career DNA™** — 7 SQLAlchemy models, 12 Pydantic schemas, 5 LLM methods + 1 data-driven
- CareerDNAService lifecycle orchestration + 10 REST endpoints
- Alembic migration for 7 Career DNA tables
- 22 tests (168/168 total passing)
- Prompt injection sanitization (8-layer OWASP LLM01 defense)
- Rate limiting on `/career-dna/generate` (3/min per user)

---

## [Ad-Hoc] — PPTS v1.1 & Code Quality — 2026-02-15

### Changed

- **PPTS v1.1**: Resolved 8 audit findings — volatile-only `session-state.json` (v2.1.0), slimmed `session-context.md` (102→51 lines), staleness detection, sync verification, honest labeling, rule deduplication
- **ESLint cleanup**: Resolved all 7 lint issues (2 errors, 5 warnings → 0 problems)
  - Replaced impure `Math.random()` with `useId`-based deterministic hash (`sidebar.tsx`)
  - Moved reduced-motion check from effect to lazy `useState` initializer (`use-scroll-animation.ts`)
  - Removed unused imports (`Link`, `Image`, `useState`) and unused state setters
- Updated `sprint-tracking.md` to v1.1.0
- Updated `GEMINI.md` session file paths to `.agent/` prefix

---

## [Sprint 7] — Production Readiness — 2026-02-14

### Added

- GitHub Actions CI/CD: `ci.yml` (path-filtered lint+test+build) + `deploy.yml` (Railway + Vercel)
- Alembic migration `5d6e7f8g9h0i` — CHECK constraint on `applications.status`
- Redis-backed JWT token blacklist (`token_blacklist.py`) with SETEX auto-TTL
- `/auth/logout` endpoint with `jti`-based token revocation
- `SecurityHeadersMiddleware` — OWASP-compliant security headers (7 headers)
- ARQ async background worker with 3 task functions + cron health check
- Production CORS origins + `effective_cors_origins` property
- `.env.production.example` — documented production environment template
- `railway.toml` — Railway config-as-code with health check
- `docs/TODO-pre-production.md` — deployment checklist
- Worker service added to `docker-compose.yml`

### Changed

- `security.py` — access tokens now include `jti` claim for revocation
- `Dockerfile.worker` CMD updated from placeholder to ARQ entrypoint
- `pyproject.toml` — added `arq`, `bcrypt`, `aiosqlite` dependencies
- `main.py` — environment-aware CORS using `effective_cors_origins`

---

## [Ad-Hoc] — Agent Customization Architecture — 2026-02-14

### Added

- `GEMINI.md` global rules file (cross-workspace identity, principles, code standards)
- Workspace rules: `architecture.md`, `documentation.md` (2 new)
- Workflows: `/review` (quality gate), `/migrate` (Alembic lifecycle) (2 new)
- `docs/AGENT_ARCHITECTURE.md` — comprehensive 3-layer system reference
- `docs/MCP_ARCHITECTURE.md` — MCP server strategy and expansion plan

### Changed

- Enhanced `coding-style.md` with Python/FastAPI standards
- Enhanced `security.md` with GDPR compliance and AI pipeline safety
- Enhanced `testing.md` with pytest conventions and example patterns
- Updated `/deploy` workflow with PathForge-specific Vercel + Railway config
- Updated `session-state.json` capabilities: rules 6→8, workflows 14→16

---

## [Sprint 6b] — Analytics — 2026-02-14

### Added

- **Funnel pipeline**: `FunnelEvent` model + 3 endpoints (record, metrics, timeline)
- **Market intelligence**: `MarketInsight` model + 2 endpoints (list, generate)
- **CV A/B experiments**: `CVExperiment` model + 3 endpoints (list, create, result)
- Analytics service layer with 8 public methods + 5 compute functions
- 15 Pydantic schemas for request/response validation
- Alembic migration `4c5d6e7f8g9h` — 3 tables, 10 indexes
- Frontend analytics dashboard at `/dashboard/analytics`
- Typed API client with 10 TypeScript interfaces + 8 functions
- 17 new tests (146 total, 0 failures)

### Fixed

- `FunnelEventResponse` metadata field mapping (`validation_alias="metadata_"`)

---

## [Sprint 6a.1] — Performance Optimization — 2026-02-14

### Added

- `useScrollState` hook — singleton scroll listener using `useSyncExternalStore`
- `@next/bundle-analyzer` integration with `analyze` script
- CSS-only scroll progress indicator using `animation-timeline: scroll()`

### Changed

- `TestimonialsMarquee` and `FaqAccordion` converted to dynamic imports (`next/dynamic`)
- `BackToTop` and `NavScrollEffect` refactored to use shared `useScrollState` hook
- `ScrollProgress` converted from JavaScript client component to pure CSS server component
- All hero/testimonial images converted to WebP format (30-70% size reduction)

### Fixed

- Infinite re-render loop in `useScrollState` — fixed with module-level `SERVER_SNAPSHOT` constant

---

## [Sprint 6a] — Navbar & UI Excellence — 2026-02-13

### Added

- Floating pill navbar with custom `--breakpoint-nav: 860px`
- Desktop CTA cluster with gradient border (primary→accent)
- Full-screen mobile drawer with React portal + staggered animations
- Hamburger↔X morphing toggle with pixel-perfect alignment
- `ThemeToggle` component with `sm`/`lg` variants + hydration safety
- `next-themes` integration with `ThemeProvider`
- Theme-aware logos (`logo-light.png` / `logo-dark.png`) via CSS switching
- Light mode color palette (oklch-based)
- Dark-scoped gradient-text, glass-card, elevated-card, problem-card styles
- Body scroll lock + Escape key handler on mobile drawer
- Development Workflow documentation (`docs/DEVELOPMENT_WORKFLOW.md`)
- Gitflow strategy: `main` (dev) + `production` (releases)
- Conventional Commits convention

### Changed

- Nav section renames: "How it Works" → "The Process", "Comparison" → "Pricing"
- Social icons + theme toggle scaled 10% for mobile touch targets

### Fixed

- Hydration mismatch — replaced `typeof document` check with `useSyncExternalStore`

---

## [Sprint 5] — Application Flow — 2026-02-12

### Added

- Application Kanban pipeline with status tracking
- Company blacklist system with current employer protection
- Rate limiting controls (10/hour, 30/day)
- Retrospective Audit — 11 findings remediated across 12 files

---

## [Sprint 4] — Web App — 2026-02-11

### Added

- Next.js 15 landing page (marketing site)
- Waitlist system with hero form
- Testimonials marquee with animated border glow
- FAQ accordion section
- Footer redesign (status badge, NL trust badge, Company column)
- Back-to-top button with glass effect
- Navbar scroll glass effect
- Interactive CSS enhancements (265+ lines)

---

## [Sprint 3] — Job Aggregation — 2026-02-10

### Added

- Adzuna API provider with salary data
- Jooble API provider with multilingual support
- Job deduplication pipeline
- Embedding pipeline for job listings
- 13 AI service unit tests

---

## [Sprint 1-2] — Foundation + AI Engine — 2026-02-09

### Added

- Monorepo setup (pnpm workspace, Turborepo)
- FastAPI backend (Python 3.12+)
- PostgreSQL + pgvector database schema
- JWT authentication with refresh tokens
- Docker Compose for local development
- Alembic migration framework
- Resume parser (AI-powered structured extraction)
- Voyage AI v4 embedding integration
- Semantic matching engine (cosine + HNSW)
- CV tailoring pipeline (LLM-powered)
- Architecture document (ARCHITECTURE.md v2.0.0)
- Brand constants framework
- GitHub repository setup
