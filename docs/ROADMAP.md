# PathForge — Live Sprint Board

> **Single Source of Truth** for all sprint tracking and task management.
> **Last Updated**: 2026-03-02 | **Current Phase**: I (Mobile) — Sprint 33 complete
> **Document ownership (ADR-010)**: Phase-level definitions live in `ARCHITECTURE.md` Section 7. This file tracks sprint-level execution.

---

## How This File Works

| Symbol | Meaning               |
| :----- | :-------------------- |
| `[x]`  | Task completed        |
| `[/]`  | Task in progress      |
| `[ ]`  | Task not started      |
| `[-]`  | Task deferred/skipped |
| ✅     | Sprint complete       |
| 📋     | Current sprint        |
| ⏳     | Upcoming sprint       |

> **Rules**: Sprint definitions come from `docs/architecture/ARCHITECTURE.md` Section 7.
> This file is the ONLY place where task status is tracked — never in `session-state.json` or `session-context.md`.

---

## Phase A: Core Platform (MVP)

### Sprint 1-2 — Foundation + AI Engine (✅ Complete)

> Combined into a single execution block. Original definition: Monorepo, FastAPI, DB schema, JWT auth, Docker, Alembic + Resume parsing, embeddings, semantic matching, CV tailoring.

- [x] Monorepo setup (pnpm workspace, Turborepo)
- [x] FastAPI backend with Python 3.12+
- [x] PostgreSQL + pgvector database schema
- [x] JWT authentication + refresh tokens
- [x] Docker Compose for local development
- [x] Alembic migration setup
- [x] Resume parser (AI-powered structured extraction)
- [x] Voyage AI v4 embedding integration
- [x] Semantic matching engine (cosine similarity + HNSW)
- [x] CV tailoring pipeline (LLM-powered)
- [x] Architecture document (ARCHITECTURE.md v2.0.0)
- [x] Market Viability Report — Digital Anthropologist analysis

### Sprint 3 — Job Aggregation (✅ Complete)

> Original definition: Adzuna/Jooble API integration, deduplication, embedding pipeline.

- [x] Adzuna API provider implementation
- [x] Jooble API provider implementation
- [x] Job deduplication pipeline
- [x] Embedding pipeline for job listings
- [x] 13 AI service unit tests

### Sprint 4 — Web App (✅ Complete)

> Original definition: Next.js UI, onboarding, Career Radar dashboard, interview prep.

- [x] Next.js 15 landing page (marketing site)
- [x] Waitlist system + hero form
- [x] Testimonials marquee section
- [x] FAQ accordion section
- [x] Footer redesign (status badge, NL trust badge, Company column)
- [x] Interactive CSS enhancements (265+ lines)
- [x] Back-to-top button component
- [x] Navbar scroll glass effect

### Sprint 5 — Application Flow (✅ Complete)

> Original definition: User-consented apply, safety controls, logging.

- [x] Application Kanban pipeline
- [x] Company blacklist system
- [x] Rate limiting controls
- [x] Retrospective Audit — 11 findings remediated across 12 files
- [x] 129/129 tests passing
- [x] Brand constants framework + GitHub repo setup

### Sprint 6a — Navbar & UI Excellence (✅ Complete, unplanned)

> **Inserted sprint**: Navbar/theme work emerged from Tier-1 quality audit. Not in original ARCHITECTURE.md definition. Sprint 6 proper (Analytics) deferred to 6b.

- [x] Floating pill navbar with custom breakpoint (860px)
- [x] Desktop CTA cluster with gradient border
- [x] Full-screen mobile drawer with portal + staggered animations
- [x] Hamburger↔X morphing toggle
- [x] ThemeToggle component + next-themes integration
- [x] Theme-aware logos (CSS-only dark/light switching)
- [x] Light mode color palette (oklch-based)
- [x] Nav section renames (Process, Pricing)
- [x] Hydration fix (useSyncExternalStore)
- [x] Gitflow strategy: main + production branches
- [x] Development Workflow documentation (13 sections)
- [x] Merge policy (sprint-end, milestone, hotfix cadences)

### Sprint 6a.1 — Performance Optimization (✅ Complete, unplanned)

> **Inserted sprint**: Performance work emerged from retrospective audit findings. Tier 1-4 optimizations.

- [x] WebP image conversion (30-70% size reduction)
- [x] Dynamic imports for TestimonialsMarquee + FaqAccordion
- [x] Scroll listener consolidation (useScrollState hook)
- [x] CSS-only ScrollProgress (animation-timeline: scroll())
- [x] @next/bundle-analyzer integration
- [x] Lucide icon audit (confirmed tree-shakeable)

### Sprint 6b — Analytics (✅ Complete)

> Resumes original Sprint 6 definition from ARCHITECTURE.md.

- [x] Funnel pipeline event tracking
- [x] Market intelligence dashboard
- [x] CV A/B tracking system

### Sprint 7 — Production Readiness (✅ Complete)

> Original definition: Expo mobile app, push notifications, security audit, monitoring.
> **Pivoted**: Mobile deferred; focused on production readiness for web platform.

- [x] GitHub Actions CI/CD pipeline (ci.yml + deploy.yml)
- [x] Alembic migration — CHECK constraint on applications.status
- [x] Redis-backed JWT token blacklist + /auth/logout endpoint
- [x] ARQ async background task queue for AI pipeline
- [x] Security headers middleware (OWASP compliance)
- [x] Production deployment configuration (Railway + Vercel)
- [x] Pre-production deployment checklist (docs/TODO-pre-production.md)

---

## Phase B: Career Intelligence (Post-MVP)

> Sprint definitions from ARCHITECTURE.md Section 7, Phase B.

### Sprint 8 — Career DNA Activation (✅ Complete)

- [x] 7 SQLAlchemy models (CareerDNA hub + 6 dimensions) with 10 StrEnums
- [x] 12 Pydantic request/response schemas
- [x] Versioned AI prompt templates (6 dimensions)
- [x] CareerDNAAnalyzer (5 LLM methods + 1 data-driven)
- [x] CareerDNAService lifecycle orchestration
- [x] 10 REST API endpoints with auth enforcement
- [x] Alembic migration for 7 Career DNA tables
- [x] 22 tests (168/168 total suite passing)
- [x] Tier-1 retrospective audit — 12 lint fixes applied

### Sprint 9 — Career Threat Radar™ (✅ Complete)

> **Hardening carry-over from Sprint 8 audit:**

- [x] ⚠️ Prompt injection sanitization — 8-layer OWASP LLM01 defense
- [x] ⚠️ Rate limiting on `/career-dna/generate` — 3/min per user (slowapi)
- [x] Quality Gate Research — 8 competitors, 4 proprietary innovations defined

> **Career Threat Radar™ features:**

- [x] 🔥 Career Resilience Score™ — 5-factor composite adaptability metric (0–100)
- [x] 🔥 Skills Shield™ Matrix — skills classified as shields (protective) vs exposures (vulnerable)
- [x] 🔥 Threat→Opportunity Inversion Engine — every threat auto-paired with actionable opportunity
- [x] 🔥 Career Moat Score — 4-dimension career defensibility metric (0–100)
- [x] Automation risk scoring — hybrid ONET Frey-Osborne + LLM contextual analysis
- [x] Industry trend monitoring — LLM-powered personalized trend analysis
- [x] Alert engine — severity-tiered, event-driven, user preference-filtered
- [x] 6 data models, 10 API endpoints, Signal Fusion Engine
- [x] 25 new tests (202/202 total passing)
- [x] Tier-1 retrospective audit — 2 lint fixes applied

### Sprint 10 — Skill Decay & Growth Tracker (✅ Complete)

- [x] Skill freshness scoring
- [x] Market demand curves
- [x] Skill Velocity Map
- [x] Personalized reskilling paths

> **Implementation detail:**
>
> - 5 SQLAlchemy models (SkillFreshness, MarketDemandSnapshot, SkillVelocityEntry, ReskillingPathway, SkillDecayPreference) + 4 StrEnums
> - 11 Pydantic request/response schemas
> - 4 versioned AI prompt templates (freshness, demand, velocity, reskilling)
> - SkillDecayAnalyzer (4 LLM methods + 4 static math helpers)
> - SkillDecayService pipeline orchestration (687 lines)
> - 9 REST API endpoints at `/api/v1/skill-decay`
> - Alembic migration `8g9h0i1j2k3l` — 5 tables with indexes
> - 38 new tests (246/246 total suite passing)
> - Tier-1 retrospective audit — 4 findings resolved, 3 MyPy errors fixed
> - Shell conventions skill + 12 workflow `&&` fixes

### Sprint 11 — Salary Intelligence Engine™ (✅ Complete)

- [x] Personalized salary calculation
- [x] Skill→salary impact modeling
- [x] Historical trajectory tracking

> **Implementation detail:**
>
> - 5 SQLAlchemy models (`SalaryEstimate`, `SkillSalaryImpact`, `SalaryHistoryEntry`, `SalaryScenario`, `SalaryPreference`) + 3 StrEnums
> - 13 Pydantic schemas with `data_source` + `disclaimer` transparency fields
> - 4 versioned AI prompt templates (salary range, skill impacts, trajectory, scenario)
> - SalaryIntelligenceAnalyzer (4 LLM methods + 4 static helpers, centralized `MAX_LLM_CONFIDENCE`)
> - SalaryIntelligenceService pipeline orchestration (~540 lines)
> - 10 REST endpoints at `/api/v1/salary-intelligence` with auth + rate limiting
> - Alembic migrations `9j0k1l2m3n4o` (5 salary tables) + `0a1b2c3d4e5f` (4 CareerDNA profile columns)
> - CareerDNA enhanced: `primary_industry`, `primary_role`, `location`, `seniority_level` columns
> - 41 new tests (287/287 total suite passing)
> - Tier-1 retrospective audit — 3 gaps addressed (G1: columns, G2: guardrails, G3: label)

### Sprint 12 — Transition Pathways (✅ Complete)

- [x] Anonymized career movement patterns
- [x] Proven pivot paths
- [x] Success probability modeling

> **Implementation detail:**
>
> - 5 SQLAlchemy models (`TransitionPath`, `SkillBridgeEntry`, `TransitionMilestone`, `TransitionComparison`, `TransitionPreference`) + 4 StrEnums
> - 15 Pydantic request/response schemas with `data_source` + `disclaimer` transparency fields
> - 4 versioned AI prompt templates (transition analysis, skill bridge, milestones, role comparison)
> - TransitionPathwaysAnalyzer (4 LLM methods + 4 static helpers, `MAX_TRANSITION_CONFIDENCE` 0.85 cap)
> - TransitionPathwaysService pipeline orchestration (~500 lines)
> - 11 REST endpoints at `/api/v1/transition-pathways` (dashboard, explore, what-if, compare, milestones, preferences)
> - Alembic migration `1a2b3c4d5e6f` — 5 tables with FK CASCADE + indexes
> - 43 new tests (330/330 total suite passing)
> - Tier-1 retrospective audit — 8 code quality fixes (ruff lint, MyPy types, model annotations)

### Sprint 13 — Career Simulation Engine™ (✅ Complete)

- [x] "What-if" career scenario simulation
- [x] ROI calculation & comparison
- [x] Confidence-capped AI projections

> **Implementation detail:**
>
> - 5 SQLAlchemy models (`CareerSimulation`, `SimulationInput`, `SimulationOutcome`, `SimulationRecommendation`, `SimulationPreference`) + 3 StrEnums
> - 14 Pydantic schemas with `ConfigDict(from_attributes=True)` + `data_source` + `disclaimer` transparency fields
> - 4 versioned AI prompt templates (scenario analysis, projection, recommendation, comparison)
> - CareerSimulationAnalyzer (4 LLM methods + 4 static helpers + 3 clamping validators)
> - CareerSimulationService pipeline orchestration (~600 lines)
> - 11 REST endpoints at `/api/v1/career-simulation` (dashboard, 5 scenario types, comparison, preferences)
> - Alembic migration `2b3c4d5e6f7g` — 5 tables with FK CASCADE + indexes + `CheckConstraint` (confidence ≤ 0.85)
> - Pagination on dashboard/list endpoints (offset/limit with total count)
> - 52 new tests (382/382 total suite passing)
> - Tier-1 retrospective audit — 4 findings resolved (R1 docstring, R2 CHECK constraint, R3 pagination, R4 ConfigDict)
> - 3 proprietary innovations: Career Scenario Simulator™, Scenario Confidence Metric™, ROI Calculator™

### Sprint 14 — Interview Intelligence™ (✅ Complete)

- [x] Company intelligence & interview prep
- [x] Predicted interview questions (5 categories)
- [x] STAR examples mapped to Career DNA

> **Implementation detail:**
>
> - 5 SQLAlchemy models (`InterviewPrep`, `CompanyInsight`, `InterviewQuestion`, `STARExample`, `InterviewPreference`) + 4 enums
> - 14 Pydantic schemas with `ConfigDict(from_attributes=True)` + `data_source` + `disclaimer` transparency fields
> - 5 versioned AI prompt templates (company analysis, questions, STAR, negotiation, comparison)
> - InterviewIntelligenceAnalyzer (5 LLM methods + 4 validators + confidence clamp)
> - InterviewIntelligenceService (10 public + 12 private methods, 680 lines)
> - 11 REST endpoints at `/api/v1/interview-intelligence` (dashboard, prep, compare, preferences, questions, STAR, negotiation)
> - Alembic migration `3c4d5e6f7g8h` — 5 tables with FK CASCADE + indexes + CheckConstraint (confidence ≤ 0.85)
> - Salary Intelligence cross-integration in negotiation scripts
> - `prep_depth` Literal type validation (`quick | standard | comprehensive`)
> - Architecture reference archived to `docs/architecture/sprint-14-interview-intelligence.md`
> - 56 new tests (438/438 total suite passing)
> - Tier-1 retrospective audit passed — 2 findings resolved (R1: Salary integration, R2: prep_depth Literal)
> - 3 proprietary innovations: Career DNA Interview Mapper™, Negotiation Script Engine™, Company Culture Decoder™
> - DRY refactor: Sprint 12 routes refactored with `_build_scan_response` helper + `model_validate()` (-218 lines)
> - MyPy type overhaul: 15→0 errors across 6 files + bonus `_build_full_response` simplification in career_simulation

## Phase C: Network Intelligence

### Sprint 15 — Hidden Job Market Detector™ (✅ Complete)

- [x] Company growth signal monitoring
- [x] Career DNA → signal matching
- [x] AI-generated outreach templates

> **Implementation detail:**
>
> - 5 SQLAlchemy models (`CompanySignal`, `SignalMatchResult`, `OutreachTemplate`, `HiddenOpportunity`, `HiddenJobMarketPreference`) + 4 StrEnums
> - 15 Pydantic schemas with `data_source` + `disclaimer` transparency fields
> - 4 versioned AI prompt templates (signal analysis, matching, outreach, opportunity surfacing)
> - HiddenJobMarketAnalyzer (4 LLM methods + 4 static helpers + 4 clamping validators, `MAX_SIGNAL_CONFIDENCE` 0.85 cap)
> - HiddenJobMarketService pipeline orchestration (~616 lines)
> - 11 REST endpoints at `/api/v1/hidden-job-market` (dashboard, scan, preferences, compare, opportunities, signals)
> - Alembic migration `4d5e6f7g8h9i` — 5 tables with FK CASCADE + indexes + CheckConstraint (confidence ≤ 0.85)
> - Input sanitization via `sanitize_user_text` on all LLM inputs
> - `LLMError` try/except with safe fallbacks on all 4 LLM methods
> - Architecture reference archived to `docs/architecture/sprint-15-hidden-job-market.md`
> - 56 new tests (494/494 total suite passing)
> - Tier-1 retrospective audit — 3 findings resolved (R1: import path, R2: input sanitization, R3: error handling)

### Sprint 16 — Cross-Border Career Passport™ (✅ Complete)

- [x] EQF credential mapping
- [x] Country comparison (CoL, salary, tax, demand)
- [x] Visa feasibility prediction

> **Implementation detail:**
>
> - 5 SQLAlchemy models (`CredentialMapping`, `CountryComparison`, `VisaAssessment`, `PassportScore`, `CareerPassportPreference`) + 4 StrEnums
> - 15 Pydantic schemas with `data_source` + `disclaimer` transparency fields
> - 4 versioned AI prompt templates (credential mapping, country comparison, visa assessment, market demand)
> - CareerPassportAnalyzer (4 LLM methods + 4 static helpers + 4 clamping validators, `MAX_PASSPORT_CONFIDENCE` 0.85 cap)
> - CareerPassportService pipeline orchestration (~610 lines)
> - 11 REST endpoints at `/api/v1/career-passport` (dashboard, scan, credentials, comparison, visa, demand, score, preferences)
> - Alembic migration `5e6f7g8h9i0j` — 5 tables with FK CASCADE + indexes + CheckConstraint (confidence ≤ 0.85)
> - Input sanitization via `sanitize_user_text` on all LLM inputs
> - `LLMError` try/except with safe fallbacks on all 4 LLM methods
> - Architecture reference archived to `docs/architecture/sprint-16-career-passport.md`
> - 54 new tests (548/548 total suite passing)
> - Tier-1 retrospective audit — 2 optional findings (R1: getattr workaround, R2: return type widening)
> - 3 proprietary innovations: EQF Intelligence Engine™, Purchasing Power Calculator™, Visa Eligibility Predictor™

### Sprint 17 — Collective Intelligence Engine™ (✅ Complete)

- [x] AI-powered career market intelligence
- [x] Salary benchmarking (personalized to Career DNA)
- [x] Peer cohort analysis (k-anonymous)
- [x] Career Pulse Index™ (composite health score)

> **Implementation detail:**
>
> - 5 SQLAlchemy models (`IndustrySnapshot`, `SalaryBenchmark`, `PeerCohortAnalysis`, `CareerPulseEntry`, `CollectiveIntelligencePreference`) + 4 StrEnums
> - 15 Pydantic schemas with `data_source` + `disclaimer` transparency fields
> - 4 versioned AI prompt templates (industry, salary, peer cohort, career pulse)
> - CollectiveIntelligenceAnalyzer (4 LLM methods + 3 static helpers + 4 clamping validators, `MAX_CI_CONFIDENCE` 0.85 cap)
> - CollectiveIntelligenceService pipeline orchestration (~651 lines)
> - 9 REST endpoints at `/api/v1/collective-intelligence` (dashboard, scan, comparison, preferences, 4 analysis endpoints)
> - Alembic migration `6f7g8h9i0j1k` — 5 tables with FK CASCADE + indexes + CheckConstraint (confidence ≤ 0.85, cohort_size ≥ 10, pulse_score 0-100)
> - Input sanitization via `sanitize_user_text` on all LLM inputs
> - `LLMError` try/except with safe fallbacks on all 4 LLM methods
> - Career Pulse clamping recomputes score from components to ensure formula integrity
> - 49 new tests (602/602 total suite passing after Sprint 18 auth fix)
> - Tier-1 retrospective audit passed — 4 optional findings (rate limiting, caching, integration tests, parallelism)
> - 3 proprietary innovations: Career Pulse Index™, Peer Cohort Benchmarking™, Industry Trend Radar™

### Sprint 18 — Infrastructure & Auth Integration (✅ Complete)

- [x] `app.core.auth` module — canonical import path for `get_current_user` dependency
- [x] Rate limiting on all 9 Collective Intelligence endpoints (Sprint 17 R1)
- [x] Auth-aware integration test fixtures (`authenticated_user`, `auth_client`)

> **Implementation detail:**
>
> - `app/core/auth.py` (NEW) — thin re-export module, provides stable import path for auth dependencies
> - `slowapi` rate limiting on all 9 CI endpoints: 5× POST (3/min), scan (2/min), dashboard (20/min), preferences GET (30/min), preferences PUT (20/min)
> - `authenticated_user` fixture — direct DB user creation bypassing HTTP endpoints
> - `auth_client` fixture — pre-authenticated `AsyncClient` with JWT token
> - `test_auth_integration.py` (NEW) — 5 integration tests: full lifecycle (register→login→protected→refresh→re-access), fixture validation, edge cases (no-token 401, invalid-token 401)
> - Resolved 168 pre-existing `ModuleNotFoundError` test errors (429→602 total passing)
> - Tier-1 retrospective audit passed — 2 findings resolved (G1: logout deferred to E2E, G2: User type hint)

### Sprint 19 — Predictive Career Engine™ (✅ Complete)

- [x] Emerging Role Radar™ — skill-overlap + trend detection
- [x] Disruption Forecast Engine™ — per-user severity + mitigation
- [x] Proactive Opportunity Surfacing — multi-signal time-sensitive
- [x] Career Forecast Index™ — composite 4-component weighted score (unique, no competitor)

> **Implementation detail:**
>
> - 5 SQLAlchemy models (`EmergingRole`, `DisruptionForecast`, `OpportunitySurface`, `CareerForecast`, `PredictiveCareerPreference`) + 5 StrEnums
> - 14 Pydantic schemas with `data_source` + `disclaimer` transparency fields
> - 4 versioned AI prompt templates (emerging roles, disruption, opportunity, career forecast)
> - PredictiveCareerAnalyzer (4 LLM methods + 2 static helpers + 4 clamping validators, `MAX_PC_CONFIDENCE` 0.85 cap)
> - PredictiveCareerService pipeline orchestration (~594 lines)
> - 8 REST endpoints at `/api/v1/predictive-career` (dashboard, scan, 4 analysis endpoints, preferences GET/PUT)
> - Alembic migration `7g8h9i0j1k2l` — 5 tables with FK CASCADE + indexes + CheckConstraint (confidence ≤ 0.85)
> - Input sanitization via `sanitize_user_text` on all LLM inputs
> - `LLMError` try/except with safe fallbacks on all 4 LLM methods
> - OWASP LLM01 guard rails in all 4 prompt templates
> - Architecture reference archived to `docs/architecture/sprint-19-predictive-career-engine.md`
> - 71 new tests (673/673 total suite passing)
> - Tier-1 retrospective audit — all areas Tier-1 Compliant ✅
> - 2 optional findings deferred to Sprint 20 (integration tests, LLM observability)

### Sprint 20 — AI Trust Layer™ (✅ Complete)

- [x] LLM observability infrastructure (TransparencyRecord, TransparencyLog, confidence scoring)
- [x] Transparency LLM wrappers (`complete_with_transparency`, `complete_json_with_transparency`)
- [x] AI Transparency API (3 endpoints: health, analyses, analysis detail)
- [x] Career DNA service integration PoC (5 analyzer methods + service layer)
- [x] R1: Persistence layer for TransparencyLog (SQLAlchemy model + Alembic migration + async DB writes)
- [x] R2: Rate limiting on AI Transparency endpoints (30/min health, 20/min analyses)
- [x] R3: Per-method transparency unit tests (10 tests covering all 5 analyzer methods)
- [x] R4: Configurable rate limits on AI Transparency endpoints (env-var overridable)
- [x] R5: DB fallback for post-restart queries (async get_recent/get_by_id/get_user_for_analysis)
- [x] R6: Background task monitoring (persistence_failures counter + pending_persistence_count)

> **Implementation detail:**
>
> - `app/core/llm_observability.py` — `TransparencyRecord` dataclass, `TransparencyLog` thread-safe circular buffer (200/user, 1000 users max), `compute_confidence_score()` 4-signal algorithm, confidence capped at 95%
> - `app/core/llm.py` — 2 transparency wrappers maintaining backward compatibility with existing completion functions
> - `app/schemas/ai_transparency.py` — 3 Pydantic v2 response models (`AIAnalysisTransparencyResponse`, `RecentAnalysesResponse`, `AIHealthResponse`)
> - `app/api/v1/ai_transparency.py` — 3 REST endpoints at `/api/v1/ai-transparency` (public health dashboard, auth-gated analyses list + detail)
> - `app/ai/career_dna_analyzer.py` — all 5 LLM methods return `tuple[data, TransparencyRecord | None]` with `analysis_type` + `data_sources` metadata
> - `app/services/career_dna_service.py` — `_log_transparency()` helper, 4 `_compute_*` helpers log records per user
> - 44 new tests: 33 unit (`test_llm_observability.py`), 8 API (`test_ai_transparency_api.py`), 3 integration (`test_ai_transparency_integration.py`)
> - 717/717 total suite passing (full regression)
> - Tier-1 retrospective audit — all 9 domains Tier-1 Compliant ✅
> - 3 optional findings deferred (persistence layer, health rate limit, per-method unit tests) — **all 3 resolved in Sprint 20 Enhancements session**
> - First-mover: no competitor (LinkedIn, Indeed, Jobscan, Teal, Rezi) exposes per-analysis confidence + data sources
>
> **Sprint 20 Enhancements (R1/R2/R3):**
>
> - R1: `AITransparencyRecord` SQLAlchemy model + Alembic migration `8h9i0j1k2l3m` + async fire-and-forget DB persistence in `TransparencyLog._persist_to_db()`
> - R2: `@limiter.limit` rate limiting on all 3 AI Transparency endpoints (30/min health, 20/min analyses)
> - R3: 10 new per-method transparency unit tests in `test_career_dna_transparency.py` (5 methods × success + empty/error)
> - 727/727 total suite passing (10 net new tests)
> - Tier-1 retrospective audit (post-enhancement) — all 9 domains Tier-1 Compliant ✅
> - 3 optional non-blocking items deferred: configurable health rate limit, DB fallback for post-restart queries, background task monitoring — **all 3 resolved in Sprint 20 Enhancements Phase 2**
>
> **Sprint 20 Enhancements (R4/R5/R6):**
>
> - R4: `rate_limit_ai_health` + `rate_limit_ai_analyses` settings in `config.py`, all 3 endpoint limiters reference `settings.*`
> - R5: `get_recent()`, `get_by_id()`, `get_user_for_analysis()` converted async with DB query fallback via `_load_*_from_db()` methods
> - R6: `_persistence_failures` counter + `pending_persistence_count` property + 2 new `AIHealthResponse` fields
> - 10 tests converted sync → async with `@pytest.mark.asyncio` + R6 health assertions
> - 727/727 total suite passing (full regression)
> - Tier-1 retrospective audit (post-R4/R5/R6) — all 9 domains Tier-1 Compliant ✅
> - **Zero deferred items remain** — AI Trust Layer™ fully production-grade

### Sprint 21 — Career Action Planner™ (✅ Complete)

- [x] Career Sprint Methodology™ — time-boxed career development cycles
- [x] Intelligence-to-Action Bridge™ — converts intelligence → actions
- [x] Adaptive Plan Recalculation™ — dynamic re-prioritization
- [x] R1: Typed pipeline DTOs (3 frozen dataclasses replacing `dict[str, Any]`)
- [x] R2: Mocked LLM integration tests (12 tests covering all 4 analyzer methods)
- [x] R3: Security scanning tools installed (`bandit` + `pip-audit`)
- [x] R4: Service file split (896 → 718 lines, 4 functions extracted)

> **Implementation detail:**
>
> - 5 SQLAlchemy models (`CareerActionPlan`, `PlanMilestone`, `MilestoneProgress`, `PlanRecommendation`, `CareerActionPlannerPreference`) + 4 StrEnums
> - 14 Pydantic schemas with `data_source` + `disclaimer` transparency fields
> - 4 versioned AI prompt templates (priorities, milestones, progress evaluation, recommendations)
> - CareerActionPlannerAnalyzer (4 LLM methods + 4 static helpers + 4 clamping validators, `MAX_PLAN_CONFIDENCE` 0.85 cap)
> - CareerActionPlannerService pipeline orchestration (~718 lines) + `_career_action_planner_helpers.py` (218 lines)
> - 3 typed pipeline DTOs: `DashboardResult`, `GeneratePlanResult`, `ComparePlansResult` (frozen dataclasses)
> - 10 REST endpoints at `/api/v1/career-action-planner` (dashboard, scan, detail, status, milestones, progress, compare, preferences)
> - Alembic migration `0a1b2c3d4e5g` — 5 tables with FK CASCADE + indexes + CheckConstraint (confidence ≤ 0.85)
> - Input sanitization via `sanitize_user_text` on all LLM inputs
> - `LLMError` try/except with safe fallbacks on all 4 LLM methods
> - 73 new tests + 12 mocked LLM integration tests (800/800 total suite passing)
> - Tier-1 retrospective audit passed — 4 findings resolved (R1: typed DTOs, R2: LLM tests, R3: security tools, R4: service split)
> - 3 proprietary innovations: Career Sprint Methodology™, Intelligence-to-Action Bridge™, Adaptive Plan Recalculation™

---

## Phase D: Career Orchestration

### Sprint 22 — Career Orchestration Layer (✅ Complete)

- [x] Unified Career Command Center™ — 12-engine dashboard with Career Vitals™ score
- [x] Notification Engine™ — event-driven notifications with preference filtering
- [x] User Profile & GDPR Data Export — Article 20+ compliant export pipeline
- [x] Alembic migration `0b1c2d3e4f5g` — 7 tables (3 features)
- [x] Test coverage remediation (+28 service-layer tests)
- [x] SQLite UUID compatibility fix (conftest.py)

> **Implementation detail:**
>
> - 3 SQLAlchemy model files (career_command_center.py, notification.py, user_profile.py) — 7 models + 8 StrEnums
> - 3 Pydantic schema files — 30+ schemas with `data_source` + `disclaimer` transparency fields
> - 3 service files — CareerCommandCenterService (~737L), NotificationService (~435L), UserProfileService (~544L)
> - 3 API router files — 23 REST endpoints across `/api/v1/career-command-center`, `/api/v1/notifications`, `/api/v1/user-profile`
> - Alembic migration `0b1c2d3e4f5g` — 7 tables with FK CASCADE + indexes + CHECK constraints (confidence ≤ 0.85)
> - Career Vitals™ score: weighted composite from 12 engines, bounded 0-100, confidence-capped at 85%
> - Engine Heartbeat™: 4-tier classification (active/idle/dormant/offline) + trend detection
> - Notification Engine: severity tiers, digest scheduling (daily/weekly/monthly), quiet hours support
> - GDPR Export: JSON package with AI methodology disclosure, SHA-256 checksums, 1-export-per-24h rate limit
> - 101 Sprint 22 tests (39 CCC + 35 Notification + 27 Profile) — 901/901 total suite passing
> - Tier-1 retrospective audit — all areas Tier-1 Compliant ✅
> - 4 deferred findings resolved: MyPy cleanup, conftest TYPE_CHECKING, async export queue, email digest delivery ✅

### Sprint 23 — Delivery Layer (✅ Complete)

- [x] Cross-Engine Recommendation Intelligence™ — multi-engine fusion with Priority-Weighted Score™
- [x] Career Workflow Automation Engine™ — 5 Smart Workflow Templates™ with trigger-based activation
- [x] 115 Sprint 23 tests (80 unit + 35 integration) — 1,016/1,016 total suite passing
- [x] Tier-1 retrospective audit — all areas Tier-1 Compliant ✅
- [x] Audit remediation: Alembic migration `0c2d3e4f5g6h` (8 tables) + pip 25.2→26.0.1 (CVE-2026-1703)
- [x] Security: `python-jose` → `PyJWT 2.11.0` (eliminates ecdsa CVE-2024-23342) + cryptography 46.0.4→46.0.5 (CVE-2026-26007)
- [x] pip-audit: **0 known vulnerabilities**

> **Implementation detail:**
>
> - 2 model files (recommendation_intelligence.py, workflow_automation.py) — 8 models + 6 StrEnums
> - 2 Pydantic schema files — 15+ schemas with `data_source` + `disclaimer` transparency fields
> - 2 service files — RecommendationIntelligenceService (~722L) + WorkflowAutomationService (~575L)
> - 2 API router files — 19 REST endpoints across `/api/v1/recommendations`, `/api/v1/workflows`
> - Priority-Weighted Score™: urgency(0.40) × impact(0.35) × inverse_effort(0.25), bounded 0-100
> - Confidence cap at 0.85 (CheckConstraint enforced) — prevents AI overconfidence
> - Cross-Engine Correlation Map™: per-recommendation engine attribution + strength scores
> - 5 Smart Workflow Templates™: Skill Acceleration, Threat Response, Opportunity Capture, Salary Negotiation, Career Review
> - 115 new tests: 80 unit (enums, models, algorithms, templates, schemas) + 35 integration (service methods, status transitions, error paths)
> - Bandit security scan: 3 pre-existing Low (JWT B105) / 38,142 LOC
> - JWT library: `python-jose` → `PyJWT 2.11.0` — eliminates `ecdsa` CVE-2024-23342 transitive dependency

---

## Phase E: Integration Layer

### Sprint 24 — API Client & Auth Integration (✅ Complete)

- [x] TypeScript API client with typed request/response (8 domain modules)
- [x] Auth context provider (JWT token management, refresh, logout)
- [x] Protected route guards (AuthGuard with returnTo, GuestGuard)
- [x] API error handling and retry logic (TanStack Query v5)
- [x] Data fetching hooks — health, Career DNA, Command Center, notifications
- [x] Backend health check integration (30s polling)

> **Implementation detail:**
>
> - `lib/http.ts` — `fetchWithAuth` with auto-refresh on 401, `ApiError` class, `fetchPublic`, 5 convenience methods (get/post/put/patch/del)
> - `lib/token-manager.ts` — SSR-safe localStorage + in-memory cache, multi-tab sync via `storage` events
> - `lib/refresh-queue.ts` — single-flight token refresh preventing race conditions
> - `providers/auth-provider.tsx` — `useReducer` 4-state machine (idle/loading/authenticated/unauthenticated), session restore, multi-tab sync
> - `providers/query-provider.tsx` — TanStack Query v5 client with smart retry (skip 4xx), 5min stale time
> - `types/api/` — 8 type files (common, auth, health, career-dna, threat-radar, career-command-center, notifications, user-profile) mirroring Pydantic schemas
> - `lib/api-client/` — 8 domain API client modules (auth, users, health, career-dna, threat-radar, career-command-center, notifications, user-profile)
> - `lib/query-keys.ts` — centralized typed query key factory with `as const` tuples
> - `hooks/api/` — 4 hook files (use-health, use-career-dna, use-command-center, use-notifications) with auth-gated queries
> - `components/auth/auth-guard.tsx` — client-side route protection with `returnTo` parameter
> - `components/auth/guest-guard.tsx` — redirects authenticated users away from login/register
> - 30 new files total, 0 regressions, 1016/1016 backend tests passing
> - Tier-1 retrospective audit — all areas Tier-1 Compliant ✅
> - `lib/api-client/` directory (not `lib/api/`) to coexist with legacy `lib/api.ts` monolith
>
> **Audit Remediation (R1/R2) + Test Coverage:**
>
> - R1: Legacy `lib/api.ts` migration — 10 consumer files migrated to domain-split `lib/api-client/`, legacy file deleted
> - R2: `AbortController` support — optional `signal` property in `RequestOptions`, forwarded to native `fetch`
> - Vitest infrastructure: `vitest.config.mts` + `test-helpers.ts` + `happy-dom` + `@vitest/coverage-v8`
> - 60 frontend tests (5 suites): `http.test.ts` (20), `token-manager.test.ts` (9), `refresh-queue.test.ts` (7), `auth.test.ts` (4), `domains.test.ts` (20)
> - Coverage thresholds enforced: 80% lines, 75% branches, 80% functions, 80% statements
> - Tier-1 audit (post-remediation) — all 8 areas Tier-1 Compliant ✅, 3 optional enhancements deferred (CI coverage gate, hook tests, provider tests)
>
> **O1/O2/O3 Enhancements:**
>
> - O1: `pnpm test` step added to CI `web-quality` job (lint → test → build)
> - O2: 16 hook tests (`hooks.test.ts`) — auth-gating, query delegation, mutation triggers + invalidation for all 4 hook files
> - O3: 18 AuthProvider tests (7 reducer pure-function + 10 integration + 1 useAuth guard) + 4 QueryProvider tests (retry logic, window focus)
> - Exported `authReducer`, `initialState`, `AuthState`, `AuthAction` for pure-function testing
> - Dependencies: `@testing-library/react`, `@testing-library/dom` added as devDependencies
> - Final count: **98 frontend tests** (8 suites, 2.77s) — Tier-1 audit all 5 areas Compliant ✅

### Sprint 25 — Core User Flow (✅ Complete)

- [x] FileUpload component — drag-drop + click-to-browse + client-side validation
- [x] Onboarding wizard upgrade — 5-step flow (upload → parse → DNA → readiness → dashboard)
- [x] Career DNA Readiness Score™ — SVG circular progress + 6-dimension indicators (innovation)
- [x] Dashboard — dynamic data from TanStack Query hooks + conditional CTA
- [x] Settings — profile CRUD + GDPR data export (Art. 20)
- [x] TanStack Query hooks — `useUserProfile`, `useOnboardingStatus`, `useUpdateProfile`, `useRequestDataExport`
- [x] 23 new frontend tests (3 suites) — 121/121 total passing
- [x] Architecture decision record — `docs/architecture/sprint-25-core-user-flow.md`
- [x] Tier-1 retrospective audit — all areas Tier-1 Compliant ✅

> **Implementation detail:**
>
> - `components/file-upload.tsx` (NEW) — drag-and-drop + click-to-browse, 5MB limit, .txt/.pdf/.doc/.docx accept, accessibility (keyboard, ARIA)
> - `components/career-dna-readiness.tsx` (NEW) — Career DNA Readiness Score™ with animated SVG ring (0–100), 6 Career DNA dimensions, score-tier coloring (innovation: no competitor offers this)
> - `hooks/use-onboarding.ts` — upgraded from 4→5 steps, added `file` state + `setFile()`, `generateCareerDna()`, `careerDna` state, FileReader support for `.txt`
> - `hooks/api/use-user-profile.ts` (NEW) — 4 TanStack Query hooks (2 auth-gated queries, 2 mutations with invalidation)
> - `app/(dashboard)/dashboard/onboarding/page.tsx` — full rewrite: FileUpload + paste toggle, parse preview, DNA generation progress, Readiness Score, dashboard redirect
> - `app/(dashboard)/dashboard/page.tsx` — dynamic data from `useCareerDnaSummary`, `useOnboardingStatus`, skeleton loaders, conditional Get Started CTA
> - `app/(dashboard)/dashboard/settings/page.tsx` — profile CRUD with inline edit form, GDPR data export request, error/success feedback
> - Query keys already existed in `query-keys.ts` — `userProfile.profile()`, `userProfile.onboarding()`, etc.
> - 23 new tests: `use-user-profile.test.ts` (7), `file-upload.test.tsx` (8), `use-onboarding.test.ts` (8)
> - 12-competitor analysis: Eightfold, Gloat, Workday, LinkedIn, Indeed, Glassdoor, Teal, Jobscan, Huntr, O\*NET, BLS, Levels.fyi
> - First-mover position confirmed: no platform generates individual-owned career intelligence during onboarding
> - ADR-025-01: .txt native, PDF/DOCX deferred; ADR-025-02: TanStack Query for all fetching; ADR-025-03: Dashboard layout auth deferred to Sprint 26

---

## Phase F: Dashboard Experience

### Sprint 26 — Career DNA & Threat Radar Dashboard (✅ Complete)

- [x] Career DNA 6-dimension visualization (pure SVG radar chart — zero deps)
- [x] Career Resilience Score™ display with 5-factor breakdown gauges
- [x] Skills Shield™ Matrix visualization (shields vs exposures with AI resistance bars)
- [x] Threat/Opportunity alert cards with severity badges + action buttons
- [x] Career Moat Score display (SVG semicircular gauge)
- [x] Dynamic readiness score (R1 resolution — computed from real dimension data)
- [x] Dashboard layout auth migration from localStorage to useAuth (R3 resolution)
- [x] 30 new frontend tests (3 suites) — 151/151 total passing
- [x] Tier-1 retrospective audit — all areas Tier-1 Compliant ✅

> **Implementation detail:**
>
> - Phase 0: `layout.tsx` auth migration from `localStorage.getItem()` to `useAuth()` hook (ADR-025-03 resolved), sidebar URL fix `/threats` → `/threat-radar`, `session-state.json` fix
> - `hooks/api/use-threat-radar.ts` (NEW) — 6 TanStack Query hooks: overview, resilience, skills shield, alerts (paginated), trigger scan, update alert
> - `hooks/api/use-career-dna.ts` — 5 new dimension hooks: skill genome, experience blueprint, growth vector, values profile, market position
> - `components/dashboard/career-dna-radar.tsx` (NEW) — Pure SVG hexagonal radar chart with gradient fill, animated transitions, skeleton loading
> - `components/dashboard/score-gauge.tsx` (NEW) — Reusable SVG semicircular gauge (0–100), 4-tier color coding
> - `components/dashboard/alert-card.tsx` (NEW) — Threat alert card with severity badges (critical/high/medium/low), expandable description, action buttons
> - `components/dashboard/skills-shield-matrix.tsx` (NEW) — Two-column shield vs exposure matrix with protection score gauge, AI resistance + market demand bars
> - `app/(dashboard)/dashboard/career-dna/page.tsx` (NEW) — Full Career DNA sub-page with dynamic readiness score, radar chart, skill genome table, 4 dimension cards
> - `app/(dashboard)/dashboard/threat-radar/page.tsx` (NEW) — Full Threat Radar sub-page with resilience gauge, career moat, skills shield matrix, paginated alerts
> - `app/(dashboard)/dashboard/page.tsx` — wired to live Threat Radar data, dynamic completeness_score, Threat Level card links to `/dashboard/threat-radar`
> - 30 new tests: `use-threat-radar.test.ts` (13), `career-dna-radar.test.tsx` (7), `alert-card.test.tsx` (11)
> - Quality Gate architecture document: 12-platform competitive analysis, 5/6 features first-to-market
> - Sprint 25 audit tracked items resolved: R1 (dynamic readiness) → Phase 2, R3 (auth migration) → Phase 0, R2 (PDF/DOCX) → deferred Sprint 29

### Sprint 27 — Intelligence Hub (✅ Complete)

- [x] Skill Decay tracker with freshness indicators + velocity map
- [x] Salary Intelligence display with skill impact modeling
- [x] Career Simulation "what-if" interface (5 scenario types)
- [x] Transition Pathways explorer with success probability
- [x] Shared intelligence card component system (IntelligenceCard 5-slot + HeadlineInsight)
- [-] Career Resilience Score™ historical trend line — Sprint 26 audit O2 → deferred O3

> **Sprint 27 Deliverables**: 25 new files + 4 modified. 50 TypeScript interfaces, 41 API methods, 26 query keys, 32 hooks, 8 components, 4 dashboard pages, sidebar navigation updated. 53 new tests (total: 204/204 frontend, 1016/1016 backend). Tier-1 audit: all 8 areas compliant ✅.

### Sprint 28 — Network Intelligence & Command Center (✅ Complete)

- [x] Hidden Job Market signal feed with outreach templates
- [x] Cross-Border Passport comparison tool
- [x] Interview Intelligence prep interface
- [x] Career Command Center (unified 12-engine dashboard)
- [x] Notification preferences UI + digest scheduling
- [x] Recommendation feed with priority-weighted sorting
- [x] Sidebar restructured with section headers (CAREER/INTELLIGENCE/COMMAND/OPERATIONS)
- [x] Actions page (merged recommendations + workflows, intelligence→action model)

> **Sprint 28 Deliverables**: 26 new files + 6 modified. 5 TypeScript type files (~77 interfaces), 5 API clients (~51 methods), 30 query keys, 7 hook files (50+ hooks), 6 dashboard pages, sidebar section headers. 27 new signal-prioritized tests (total: 232/232 frontend). Tier-1 audit: all areas compliant ✅.

---

## Phase G: Data Pipeline

### Sprint 29 — Production Data Layer (✅ Complete)

- [x] PostgreSQL + pgvector production setup (Supabase — EMBEDDING_DIM constant, SSL, pool hardening)
- [x] Alembic migration CI verification (Python scripts, drift check in CI)
- [x] Redis production configuration (rate limiter fix C1, worker SSL, config settings)
- [x] Circuit breaker for external APIs (Redis-backed, CLOSED→OPEN→HALF_OPEN)
- [x] LiteLLM production model routing (Redis budget counter, per-tier RPM guards)
- [x] Langfuse LLM observability activation (10% sampling, PII redaction hook)
- [x] PDF/DOCX server-side parsing (10MB limit, 100-page guard, MIME verification)
- [-] E2E tests for Career DNA & Threat Radar pages — deferred to Sprint 30
- [-] Job aggregation scheduled worker cron — deferred to Sprint 30

> **Sprint 29 Deliverables**: 16 files (11 modified + 5 new). 6 Critical + 5 High audit findings remediated. Redis-backed LLM budget counter + RPM sliding window, circuit breaker, PII redactor, secure document parser, Alembic CI scripts. 1,016/1,016 backend + 232/232 frontend tests passing. Tier-1 audit: all 8 areas compliant ✅.

---

## Phase H: Production Hardening

### Sprint 30 — Reliability & Observability (✅ Complete)

- [x] Sentry error tracking (API — `sentry.py` with EventScrubber, LLM fingerprinting, sampling ramp)
- [x] CD pipeline (`deploy.yml` — auto-deploy on merge to production, health check, rollback)
- [x] E2E test suite (Playwright — 8 spec files: auth, navigation, career-dna, threat-radar, command-center, actions, dashboard, intelligence-hub)
- [x] Structured JSON logging (correlation ID, PII redaction, OTel naming, env-based levels)
- [x] Performance baselines (Lighthouse + API P95 script, `docs/baselines/` placeholder)
- [x] Rate limiting with Redis backing (failover to memory://, auth endpoint protection)
- [x] Graceful shutdown in lifespan (Sentry flush, Redis close, DB dispose)
- [x] Redis failover for rate limiting (fail-open with degraded tracking)
- [x] Deferred Sprint 29 items (job aggregation cron, ARQ dead letter queue, worker pool sizing)
- [x] CI security scanning (pip-audit + pnpm audit)
- [-] Frontend Sentry (`@sentry/nextjs`) — deferred to Phase I (Senior Staff decision)

> **Sprint 30 Deliverables**: 24 files (18 modified + 6 new). 8 workstreams, 11 audit findings resolved. `sentry-sdk[fastapi]` added to dependencies, `deploy.yml` CD pipeline, 8 Playwright E2E spec files (~28 tests), `perf-baseline.sh`, `docs/baselines/sprint-30-baselines.md`. Backend: 1,016/1,016 tests, 0 lint errors. Frontend: 0 lint warnings, 0 tsc errors, 0 vulnerabilities, build passes. Tier-1 audit: all areas compliant ✅.

---

## Phase I: Mobile Platform

### Sprint 31 — Mobile Foundation + Upload (✅ Complete)

- [x] Expo SDK 52 scaffold (Expo Router v4, TypeScript strict, pnpm monorepo integration)
- [x] Shared type extraction (22 web types → `packages/shared/src/types/api/`)
- [x] CI: `mobile-quality` job (tsc + jest)
- [x] Mobile token manager (SecureStore, async hydration, in-memory cache, listener pattern)
- [x] HTTP client (15s timeouts, AbortController, transparent 401 refresh, NetworkError/ApiError)
- [x] Single-flight refresh queue (`lib/refresh-queue.ts`)
- [x] Network connectivity monitoring (`lib/network.ts`)
- [x] 5 API client modules (auth, career-dna, resume, notifications, health)
- [x] Auth flow: 4-state machine + AppState foreground check + session restore
- [x] Tab navigation with Ionicons icon system (25+ semantic pairs, TabBarIcon wrapper)
- [x] 8 UI components (Button, Input, Card, ScoreBar, Skeleton, Toast, Badge, Icon) + barrel export
- [x] `useTheme` hook (structural ThemeColors interface, memoized LIGHT/DARK)
- [x] `useResumeUpload` hook (file picking, validation, XHR progress, cancel)
- [x] Resume upload screen (camera/gallery/files + progress + cancel)
- [x] Login/Register screens with shared Input/Button, inline validation, keyboard navigation
- [x] Error boundary + offline banner components
- [x] Mobile `.gitignore`
- [x] 45 unit tests (token-manager 13, http 14, theme+config 18)
- [x] Tier-1 retrospective audit — 9.2/10, all mobile domains compliant ✅

> **Sprint 31 Deliverables**: 40+ new files. Expo SDK 52, TypeScript 5.9 strict, TanStack Query v5. 8 UI components, centralized Ionicons registry, extracted business-logic hooks. `tsc --noEmit` 0 errors, 45/45 mobile tests, 1016/1016 backend tests, 0 npm vulnerabilities. Architecture reference: `docs/architecture/sprint-31-32-mobile-platform.md`.

### Sprint 32 — Intelligence + Notifications (✅ Complete)

- [x] Backend push infrastructure (PushToken model, push_service.py, 3 API endpoints)
- [x] Career DNA mobile view (stack navigator, IntelligenceBlock, live home screen, 6-dimension detail)
- [x] Threat summary component (API client, hook, risk badge + skills shield)
- [x] Push notification client (use-push-notifications hook, settings UI, deep linking, logout deregister)
- [x] Shared types (PushTokenRegisterRequest, PushTokenStatusResponse)
- [-] Mobile tests Sprint 32 (~20 tests) — deferred R1
- [-] Alembic migration for PushToken — deferred R2
- [x] Tier-1 retrospective audit — 7/9 areas compliant, 2 partially compliant (testing, web build)

> **Sprint 32 Deliverables**: 21 files (10 modified + 11 new). 5 phases: backend push infrastructure, mobile Career DNA view, Threat Summary, push notification client, shared types. Backend: 53/53 core tests, 35/35 notification tests. Mobile: tsc 0 errors. Shared: tsc 0 errors. npm audit: 0 vulnerabilities. 6 audit findings resolved (#1, #4, #8, #12, #15, #17). 2 high-priority items deferred to Sprint 33 (Alembic migration, mobile tests).

### Sprint 33 — Testing + Migrations + Security Hardening (✅ Complete)

- [x] Alembic merge migration — 4 heads → 1 (`9i0j1k2l3m4n`), `push_tokens` table + `push_notifications` column
- [x] Security F2: `deregister_token()` ownership verification (`user_id` filter)
- [x] Security F3: Client-server contract fix (`deregisterPushToken` body payload)
- [x] Deep link router — whitelist-based `resolveDeepLink()` with safe fallback
- [x] Code extractions — `buildDimensions` → `career-dna-helpers.ts`, `getRiskColor`/`getRiskLabel` exported
- [x] 24 new mobile tests (4 suites: buildDimensions, threat helpers, push hook, deep link router)
- [x] Web build stability — pinned `@types/react` + `@types/react-dom` to exact versions
- [x] Architecture documentation — push notification flow, entity definitions updated

> **Sprint 33 Deliverables**: 14 files (8 modified + 6 new). 2 Critical security fixes (F2 ownership, F3 contract), Alembic merge migration, deep link router, 4 code extractions, 24 new mobile tests (69/69 total). Backend: 1,016/1,016 tests, 0 lint/type errors. Mobile: 69/69 tests (7 suites). Web: 232/232 tests, build ✅ (36/36 pages). Tier-1 audit: all areas compliant ✅.

#### Sprint 33 Session 2 — F4/F6/F7 Remediation + Dependabot Security

- [x] F4: Rate limit redesign — dispatch-based counter on `NotificationPreference` (`daily_push_count`, `last_push_date`)
- [x] F6: PII masking — `mask_token()` applied in `get_status()` and `register_push_token()`
- [x] F7: Connection pooling — httpx `AsyncClient` singleton with lifespan shutdown
- [x] Alembic migration `a1b2c3d4e5f6` — push rate tracking columns
- [x] 14 new backend tests (`test_push_service.py`) — 1,030/1,030 total
- [x] `rate_limit_push` config setting (10/min) on 3 push endpoints
- [x] 7 Dependabot alerts resolved (tar, serialize-javascript, minimatch via pnpm overrides)
- [x] `pnpm audit`: 0 known vulnerabilities

- [ ] Stripe billing (subscription tiers, feature gating, usage metering)
- [ ] Admin dashboard (user management, system health)
- [ ] Waitlist → onboarding conversion flow
- [ ] Public career profiles (opt-in)

---

## Ad-Hoc Work Log

> Unplanned tasks that emerged during development. These are logged here and attributed to the sprint during which they occurred.

| Date       | Task                                  | During Sprint | Status  | Notes                                        |
| :--------- | :------------------------------------ | :------------ | :------ | :------------------------------------------- |
| 2026-02-13 | Production branch setup & gitflow     | 6a            | ✅ Done | Documented in DEVELOPMENT_WORKFLOW.md        |
| 2026-02-13 | Retrospective audit remediation       | 5→6a          | ✅ Done | 11 findings across 12 files                  |
| 2026-02-14 | Performance optimization (Tier 1-4)   | 6a.1          | ✅ Done | Image, scroll, bundle optimizations          |
| 2026-02-14 | Professional Project Tracking System  | 6b            | ✅ Done | This system itself                           |
| 2026-02-14 | Sprint 6b Analytics implementation    | 6b            | ✅ Done | 3 models, 8 endpoints, 17 tests              |
| 2026-02-14 | Agent Customization Architecture      | Post-6b       | ✅ Done | GEMINI.md, 8 rules, 16 workflows             |
| 2026-02-15 | PPTS v1.1 — 8 audit findings          | Post-7        | ✅ Done | Volatile-only state, staleness detect        |
| 2026-02-15 | ESLint cleanup — 7 issues resolved    | Post-7        | ✅ Done | 0 errors, 0 warnings achieved                |
| 2026-02-16 | MyPy type annotation overhaul         | Post-9        | ✅ Done | 165→0 errors, 32 files, 3 bugs fixed         |
| 2026-02-16 | CI pipeline fix — ai extras           | Post-9        | ✅ Done | Test collection failures resolved            |
| 2026-02-16 | Contact page redesign (Tier-1)        | Post-9        | ✅ Done | 2-col layout, dept cards, FAQ grid           |
| 2026-02-16 | Navbar/footer/sitemap updates         | Post-9        | ✅ Done | Contact link, social links, JSON-LD          |
| 2026-02-16 | Pricing section + Tier-1 audit        | Post-9        | ✅ Done | 3 tiers, PricingCards, 9 audit fixes         |
| 2026-02-17 | Google Workspace + email aliases      | Post-9        | ✅ Done | emre@pathforge.eu + 4 aliases                |
| 2026-02-17 | Resend email integration              | Post-9        | ✅ Done | SPF/DKIM/DMARC DNS verified                  |
| 2026-02-17 | GA4 + Consent Mode v2                 | Post-9        | ✅ Done | G-EKGQR1ZWH3, consent-aware tracking         |
| 2026-02-17 | Google Search Console verified        | Post-9        | ✅ Done | DNS TXT record, robots.ts created            |
| 2026-02-17 | Vercel deploy pipeline setup          | Post-9        | ✅ Done | Monorepo config, auto-deploy disabled        |
| 2026-02-17 | CI/CD pnpm version fix                | Post-9        | ✅ Done | Removed explicit version from actions        |
| 2026-02-17 | GitHub Secrets (Vercel)               | Post-9        | ✅ Done | 3 secrets, deploy pipeline tested ✅         |
| 2026-02-18 | Railway API deployment                | Post-9        | ✅ Done | 3 fixes, health check verified ✅            |
| 2026-02-18 | DNS configuration (GoDaddy→Vercel)    | Post-9        | ✅ Done | pathforge.eu live, Valid Configuration       |
| 2026-02-18 | DKIM Google Workspace                 | Post-9        | ✅ Done | google.\_domainkey TXT, auth active          |
| 2026-02-18 | Vercel + Railway env vars             | Post-9        | ✅ Done | 13 Railway + 6 Vercel vars configured        |
| 2026-02-19 | Turnstile error resolution            | Post-9        | ✅ Done | useTurnstile hook, 300030/preload fix        |
| 2026-02-19 | Waitlist duplicate handling           | Post-9        | ✅ Done | Duplicate detection, diff emails, rate limit |
| 2026-02-19 | UI/UX polish session                  | Post-9        | ✅ Done | 6 issues + drag/swipe, deployed to prod      |
| 2026-02-19 | Turnstile CSP fix (execute-on-demand) | Post-9        | ✅ Done | execution: execute mode, Tier-1 audit ✅     |
| 2026-02-20 | PowerShell shell conventions          | 10            | ✅ Done | Skill created, 12 `&&` fixes across 6 files  |
| 2026-02-21 | MyPy 15→0 type warnings               | 14            | ✅ Done | 6 files, +22/−81 lines, full green CI        |
| 2026-02-24 | Sprint 22 audit fixes (4 findings)    | 22            | ✅ Done | MyPy, TYPE_CHECKING, async export, email     |

---

## Sprint Velocity

| Sprint | Planned Tasks | Completed   | Ad-Hoc Added | Sessions |
| :----- | :------------ | :---------- | :----------- | :------- |
| 1-2    | 12            | 12          | 0            | ~4       |
| 3      | 5             | 5           | 0            | ~2       |
| 4      | 8             | 8           | 0            | ~3       |
| 5      | 6             | 6           | 2            | ~3       |
| 6a     | 12            | 12          | 3            | ~3       |
| 6a.1   | 6             | 6           | 0            | 1        |
| 6b     | 3             | 3           | 2            | 1        |
| 7      | 6             | 7           | 1            | 1        |
| 8      | 3             | 9           | 1            | 2        |
| 9      | 8             | 11          | 3            | 1        |
| 10     | 4             | 10          | 1            | 2        |
| 11     | 3             | 10          | 1            | 1        |
| 12     | 3             | 11          | 0            | 1        |
| 13     | 3             | 13          | 0            | 1        |
| 14     | 3             | 12          | 1            | 1        |
| 15     | 3             | 12          | 0            | 1        |
| 16     | 3             | 11          | 0            | 1        |
| 17     | 4             | 10          | 0            | 1        |
| 18     | 3             | 3           | 0            | 1        |
| 19     | 4             | 12          | 0            | 1        |
| 20     | 7             | 7           | 0            | 2        |
| 21     | 7             | 7           | 0            | 1        |
| 22     | 6             | 6           | 1            | 3        |
| 23     | 4             | 4           | 0            | 1        |
| 24     | 6             | 15          | 0            | 3        |
| 25     | 5             | 9           | 1            | 1        |
| 26     | —             | —           | —            | —        |
| 27     | —             | —           | —            | —        |
| 28     | 6             | 8           | 0            | 1        |
| 29     | 8             | 7 (+2 def)  | 0            | 1        |
| 30     | 8             | 10 (+1 def) | 1            | 2        |
| 31     | 17            | 19          | 0            | 1        |
| 32     | 7             | 5 (+2 def)  | 0            | 2        |
| 33     | 8             | 8           | 0            | 1        |
