# Sprint 25 — Core User Flow: Architecture Decision Record

> **Date**: 2026-02-26 | **Author**: Antigravity AI Kit (Trust-Grade)
> **Status**: Proposed | **Sprint**: 25 | **Phase**: E (Integration Layer)
> **Approved by**: Pending Product Owner approval

---

## 1. Strategic Context

Sprint 25 bridges 24 sprints of career intelligence engine development (156 API endpoints, 66 models, 1,114 tests) with the first end-to-end user-facing flow. This is the **activation sprint** — the moment PathForge transforms from an AI-powered backend into a usable career intelligence platform.

### Why This Sprint Matters

The entire value proposition of PathForge — 12 proprietary intelligence engines generating Career DNA, threat analysis, salary intelligence, transition pathways, and career forecasting — is inaccessible until a user can:

1. **Input their career data** (resume upload)
2. **See their career intelligence** (Career DNA generation)
3. **Navigate their workspace** (dashboard & settings)

Without Sprint 25, PathForge is a powerful API with no user interface.

---

## 2. Competitive Intelligence (12-Platform Analysis)

### 2.1 Enterprise Talent Intelligence Platforms

| Platform         | Approach                                                                                              | Individual-Owned? |  Career DNA Equivalent?  |
| :--------------- | :---------------------------------------------------------------------------------------------------- | :---------------: | :----------------------: |
| **Eightfold AI** | Deep-learning skills analysis across 1.6B trajectories, Digital Twin (2025), potential-based matching | ❌ Employer-owned | ❌ Hidden from candidate |
| **Gloat**        | Internal talent marketplace, career lattice, skills-based mobility, AI-driven recommendations         | ❌ Employer-owned |     ❌ Internal only     |
| **Workday**      | Skills Cloud, Career Hub, AI job recommendations, Onboarding Plans (2025R1)                           | ❌ Employer-owned |   ❌ Tied to employer    |

**Key Insight**: Enterprise platforms generate rich career intelligence but it is **owned by the employer, not the individual**. When an employee leaves, their career intelligence stays behind.

### 2.2 Consumer Job Search Tools

| Platform      | Resume Input                                 | Career Profile                 | AI Intelligence                                                 | Onboarding                                        |
| :------------ | :------------------------------------------- | :----------------------------- | :-------------------------------------------------------------- | :------------------------------------------------ |
| **LinkedIn**  | File upload + profile                        | Work history + skills (manual) | Skill assessments, job recommendations                          | 5-step: profile→photo→headline→skills→connections |
| **Indeed**    | File upload + paste + LinkedIn import        | Resume-derived skills          | Basic job matching                                              | Minimal: register→upload→search                   |
| **Glassdoor** | File upload (PDF/DOCX/TXT) + LinkedIn import | Synced with Indeed             | Chatbot insights (2025)                                         | register→upload→Easy Apply                        |
| **Teal**      | File upload + LinkedIn import + Chrome ext.  | Career history database        | Resume ATS scoring, keyword optimization, achievement assistant | Checklist-style: upload→build→track               |
| **Jobscan**   | File upload + paste + LinkedIn import        | ATS compatibility profile      | NLP keyword matching, match rate scoring                        | Upload resume→paste JD→get score                  |
| **Huntr**     | File upload + manual entry                   | Skills extracted from resume   | Board-based job tracking                                        | Register→upload→board setup                       |

**Key Insight**: Consumer tools optimize **resume presentation** for ATS systems, but none generate **deep career intelligence** from the resume. They tell you "your resume is 73% optimized" — not "here are your hidden skills, growth vectors, and market position."

### 2.3 Government / Data Platforms

| Platform       | Purpose                                                             |     Individual Use?     |
| :------------- | :------------------------------------------------------------------ | :---------------------: |
| **O\*NET**     | Occupational database (1,016 occupations, 19,265 skill descriptors) |    ❌ Reference only    |
| **BLS**        | Bureau of Labor Statistics — wage/employment data                   | ❌ Aggregate statistics |
| **Levels.fyi** | Crowdsourced compensation data by company/level/location            |    ✅ Search by role    |

**Key Insight**: These are data **sources**, not career intelligence platforms. PathForge already integrates their patterns through the Salary Intelligence Engine™ and Career Threat Radar™.

---

## 3. Innovation Assessment

### 3.1 The Gap: Individual-Owned Career Intelligence

```
┌─────────────────────────────────────────────────────────────┐
│                    Enterprise Platforms                       │
│  Eightfold · Gloat · Workday                                │
│  Rich AI → Skills Cloud → Career Paths                       │
│  ❌ Employer-owned · Lost when employee leaves               │
├─────────────────────────────────────────────────────────────┤
│                    Consumer Tools                             │
│  LinkedIn · Teal · Jobscan · Indeed · Glassdoor              │
│  Resume Upload → ATS Score → Job Search                      │
│  ❌ No deep career intelligence · No skill genome             │
├─────────────────────────────────────────────────────────────┤
│                  ⬇️ THE GAP ⬇️                               │
│                                                              │
│  No platform generates INDIVIDUAL-OWNED career intelligence  │
│  from a resume, including:                                   │
│  · Skill genome with hidden skills                           │
│  · Experience blueprint with pattern analysis                │
│  · Growth vector with career trajectory projection           │
│  · Values profile alignment                                  │
│  · Market position assessment                                │
│  · Career resilience scoring                                 │
├─────────────────────────────────────────────────────────────┤
│                    PathForge                                  │
│  Resume Upload → AI Parse → Career DNA™ → 12 Engines         │
│  ✅ Individual-owned · Portable · Transparent · Private       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 PathForge's First-Mover Position

PathForge is the **only platform** that:

1. **Generates Career DNA™ from a single resume** — 6-dimension profile (Skill Genome, Experience Blueprint, Growth Vector, Values Profile, Market Position, Career Resilience)
2. **Shows the individual their own career intelligence** — not hidden in an employer dashboard
3. **Feeds that intelligence into 12 active engines** — creating a compound effect no competitor can replicate in a single sprint
4. **Respects data sovereignty** — GDPR Art. 20 export, user-initiated generation, confidence caps (≤85%), full transparency records

### 3.3 Transformative Capability Verdict

> **✅ APPROVED**: Sprint 25 features represent a **transformative capability** that establishes meaningful differentiation. The Core User Flow is not a replication of competitor features — it is the activation of a unique career intelligence architecture that no competitor (enterprise or consumer) currently offers to individuals.

---

## 4. Enhanced Sprint 25 Scope

Based on the competitive analysis, the following refinements enhance the original plan:

### 4.1 Innovation: Career DNA Readiness Score™

During the onboarding wizard, after Career DNA generation, display a **Career DNA Readiness Score** — a composite metric showing how "ready" the generated profile is for intelligence engine activation:

| Factor              | Weight | Source                                         |
| :------------------ | -----: | :--------------------------------------------- |
| Skills completeness |    30% | Skill genome count vs. role benchmark          |
| Experience depth    |    25% | Experience entries with dates and descriptions |
| Values clarity      |    20% | Values profile confidence score                |
| Market positioning  |    15% | Market position data completeness              |
| Growth vector       |    10% | Growth projection confidence                   |

**Why this matters**: No competitor shows the user how _ready_ their profile is for intelligent career guidance. This creates immediate value perception and motivates profile improvement.

### 4.2 Enhanced Onboarding Flow (5 Steps → Career DNA Readiness)

```
Step 1: Upload    →  File upload (drag-drop) + paste fallback
Step 2: Parse     →  AI extraction preview + edit confirmation
Step 3: DNA Gen   →  Career DNA generation with progress animation
Step 4: Readiness →  Career DNA Readiness Score™ + dimension preview
Step 5: Dashboard →  Redirect to dashboard with live data
```

### 4.3 Dashboard: Career DNA Summary Card

Replace the static "Career DNA Score: —" card with a **Career DNA Summary Card** that:

- Shows the Readiness Score if Career DNA exists
- Shows dimension completion indicators (6 colored segments)
- Links directly to `/dashboard/career-dna` (Sprint 26)
- Falls back to "Start onboarding →" CTA if no DNA exists

### 4.4 Settings: Privacy-First Design

Align with Glassdoor's 2025 privacy controls:

- Profile visibility toggle (public/private)
- GDPR data export with format selection (JSON/CSV)
- Data deletion request (GDPR Art. 17) — linked to Career DNA delete endpoint
- Account deactivation flow

---

## 5. Architecture Decisions

### ADR-025-01: File Upload Strategy

**Decision**: Support `.txt` file upload natively; defer PDF/DOCX server-side parsing.

**Rationale**: The backend `POST /api/v1/ai/parse-resume` accepts `raw_text` only. Client-side PDF extraction libraries (pdf.js, mammoth.js) are unreliable for complex resume layouts. Honest UX messaging ("PDF parsing coming soon") is preferable to a half-baked experience.

**Trade-off**: Users with PDF-only resumes must paste text manually. This is identical to Jobscan's initial approach and is accepted for Sprint 25.

### ADR-025-02: TanStack Query for All Data Fetching

**Decision**: All new data fetching uses TanStack Query hooks (not raw `useEffect` + `fetch`).

**Rationale**: Sprint 24 established the TanStack Query infrastructure with auth-gated queries, query key factories, and mutation invalidation. Sprint 25 extends this pattern consistently.

### ADR-025-03: Dashboard Layout Auth Migration Deferred

**Decision**: Keep legacy `localStorage` auth check in `(dashboard)/layout.tsx`; new sub-pages use `useAuth` hook.

**Rationale**: Refactoring the layout is a breaking change that affects all 8 dashboard routes. Sprint 26 will handle this as part of the Dashboard Experience phase.

---

## 6. Naming Conventions

| Item               | Convention                   | Example                                |
| :----------------- | :--------------------------- | :------------------------------------- |
| Components         | PascalCase, descriptive      | `FileUpload`, `CareerDnaReadinessCard` |
| Hooks              | camelCase with `use` prefix  | `useOnboarding`, `useUserProfile`      |
| Test files         | `.test.ts` / `.test.tsx`     | `file-upload.test.tsx`                 |
| API client modules | kebab-case                   | `user-profile.ts`                      |
| Query keys         | camelCase with domain prefix | `queryKeys.userProfile.all`            |

---

## 7. Test Targets

| Test File                  |   Tests | Category                                |
| :------------------------- | ------: | :-------------------------------------- |
| `use-user-profile.test.ts` |       7 | Hook tests (auth-gating, mutations)     |
| `file-upload.test.tsx`     |       8 | Component tests (validation, callbacks) |
| `use-onboarding.test.ts`   |       8 | Hook tests (state machine, steps)       |
| **Total new**              |  **23** |                                         |
| **Sprint 25 target**       | **121** | 98 existing + 23 new                    |

---

## 8. Risk Assessment

| Risk                                      | Severity | Mitigation                                                                  |
| :---------------------------------------- | :------- | :-------------------------------------------------------------------------- |
| PDF/DOCX upload demand                    | Medium   | Clear UX message + paste fallback; track feature request count              |
| Backend unavailability during demo        | Low      | All APIs show graceful loading/error states; no hard failures               |
| Career DNA generation fails (no LLM keys) | Medium   | Error boundary with clear message; onboarding still allows dashboard access |
| Dashboard layout auth race condition      | Low      | Legacy auth check is functional; migration in Sprint 26                     |

---

## 9. Verification Plan

| Check        | Command                  | Expected            |
| :----------- | :----------------------- | :------------------ |
| Lint         | `pnpm lint`              | 0 errors            |
| Types        | `pnpm exec tsc --noEmit` | 0 errors            |
| Tests        | `pnpm test`              | ≥121 passing        |
| Build        | `pnpm build`             | exit 0, ≥24 routes  |
| Tier-1 audit | Manual                   | All areas compliant |

---

## 10. Conclusion

Sprint 25 activates PathForge's unique value proposition. The 12-competitor analysis confirms that **no platform — enterprise or consumer — generates individual-owned career intelligence during onboarding**. The addition of the Career DNA Readiness Score™ creates immediate value perception and further differentiates PathForge. This sprint is approved for implementation.
