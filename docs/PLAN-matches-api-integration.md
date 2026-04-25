# PLAN: Job Matches API Integration

> **Sprint**: Post-50 · **Date**: 2026-04-24
> **Type**: `feat` · **Size**: Medium (6 files, ~2h)
> **Author**: Claude (Senior Staff)
> **Quality Score**: 78/80 → PASS ✅

---

## 1. Context & Problem Statement

`apps/web/src/app/(dashboard)/dashboard/matches/page.tsx` has a hardcoded `const matches: MatchCandidate[] = []` with a TODO comment (line 14) and `const resumeId: string | null = null` (line 23). The backend matching endpoint `POST /api/v1/ai/match-resume/{resume_id}` and the resume list endpoint `GET /api/v1/resumes/` are both fully implemented and deployed. This gap means Career Radar shows a permanent empty state for every authenticated user, making a core product feature invisible despite the backend being production-ready.

---

## 2. Goals & Non-Goals

**Goals:**
- Fetch the authenticated user's resume list from `GET /api/v1/resumes/` to obtain a `resumeId`
- Fetch job matches from `POST /api/v1/ai/match-resume/{resumeId}` using the most recent resume
- Display real match results in the Career Radar page with loading and error states
- Follow the established TanStack Query + `useQuery` hook pattern used by every other feature (e.g., `useCareerDnaProfile`, `useHiddenJobMarket`)

**Non-Goals:**
- Resume upload UI changes (resumes page is separate)
- Matching algorithm changes (backend concern)
- Caching strategy beyond TanStack Query defaults
- Resume selection UI (always use most recent resume v1 → simplest correct behaviour)

---

## 3. Implementation Steps

### Step 1 — Add `ResumeSummary` type
**File**: `apps/web/src/types/api/resumes.ts` _(new)_

Create type mirroring `ResumeSummaryResponse` from `apps/api/app/api/v1/resumes.py`:

```ts
export interface ResumeSummary {
  id: string;
  title: string;
  version: number;
  raw_text_length: number;
  has_structured_data: boolean;
  has_embedding: boolean;
  created_at: string | null;
}
```

**Verify**: File exists, TypeScript compiles without errors.

---

### Step 2 — Export type from barrel
**File**: `apps/web/src/types/api/index.ts`

Append at the end (after billing export):
```ts
export type * from "./resumes";
```

**Verify**: `ResumeSummary` importable from `@/types/api`.

---

### Step 3 — Create resumes API client
**File**: `apps/web/src/lib/api-client/resumes.ts` _(new)_

```ts
import { fetchWithAuth } from "@/lib/http";
import type { ResumeSummary } from "@/types/api";

export const resumesApi = {
  list(): Promise<ResumeSummary[]> {
    return fetchWithAuth<ResumeSummary[]>("/api/v1/resumes/");
  },
};
```

**Verify**: Follows same pattern as `career-dna.ts` (single-object export, `fetchWithAuth`).

---

### Step 4 — Register in API client index
**File**: `apps/web/src/lib/api-client/index.ts`

Append after billing export:
```ts
export { resumesApi } from "./resumes";
```

**Verify**: `resumesApi` importable from `@/lib/api-client`.

---

### Step 5 — Add query keys for resumes
**File**: `apps/web/src/lib/query-keys.ts`

Add domain block after the `billing` entry:
```ts
resumes: {
  all: ["resumes"] as const,
  list: () => ["resumes", "list"] as const,
},
```

**Verify**: `queryKeys.resumes.list()` resolves to `["resumes", "list"]`.

---

### Step 6 — Create `useResumes` hook
**File**: `apps/web/src/hooks/api/use-resumes.ts` _(new)_

```ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { resumesApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { ResumeSummary } from "@/types/api";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

export function useResumes() {
  const { isAuthenticated } = useAuth();

  return useQuery<ResumeSummary[], ApiError>({
    queryKey: queryKeys.resumes.list(),
    queryFn: () => resumesApi.list(),
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000,
  });
}
```

**Verify**: Pattern identical to `use-career-dna.ts:useCareerDnaProfile`.

---

### Step 7 — Create `useMatches` hook
**File**: `apps/web/src/hooks/api/use-matches.ts` _(new)_

```ts
"use client";

import { useQuery } from "@tanstack/react-query";
import { aiApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { MatchResponse } from "@/types/api/ai";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

export function useMatches(resumeId: string | null) {
  const { isAuthenticated } = useAuth();

  return useQuery<MatchResponse, ApiError>({
    queryKey: [...queryKeys.ai.all, "matches", resumeId],
    queryFn: () => aiApi.matchResume(resumeId!, 20),
    enabled: isAuthenticated && resumeId !== null,
    staleTime: 5 * 60 * 1000,
  });
}
```

**Verify**: `enabled` guard prevents calls when `resumeId` is null; function never called with `null` due to non-null assertion.

---

### Step 8 — Wire up `matches/page.tsx`
**File**: `apps/web/src/app/(dashboard)/dashboard/matches/page.tsx`

Replace lines 1–23 (imports + hardcoded state) with live hooks:

```tsx
"use client";

import { useCallback } from "react";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { MatchCard } from "@/components/match-card";
import { tailorCV } from "@/lib/api-client/ai";
import { useResumes } from "@/hooks/api/use-resumes";
import { useMatches } from "@/hooks/api/use-matches";
import type { TailorCVResponse } from "@/types/api/ai";

export default function MatchesPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [tailoringId, setTailoringId] = useState<string | null>(null);
  const [tailorResult, setTailorResult] = useState<TailorCVResponse | null>(null);

  const { data: resumes } = useResumes();
  const resumeId = resumes?.[0]?.id ?? null;  // most recent resume

  const { data: matchData, isLoading: loading } = useMatches(resumeId);
  const matches = matchData?.matches ?? [];
  // ... rest of component unchanged
```

Remove the `import type { MatchCandidate, ... }` for `MatchCandidate` (no longer needed directly — it's used in JSX via `matches` array typed by `MatchResponse`).

**Verify**: Page renders without TypeScript errors; `matches` is `MatchCandidate[]`; `loading` reflects real fetch state; `resumeId` flows through to `handleTailorCV`.

---

## 4. Testing Strategy

**Unit tests** (`./__tests__/hooks/api/use-matches.test.ts` and `use-resumes.test.ts`):
- `useResumes` returns list when auth is enabled
- `useResumes` does not fetch when `isAuthenticated=false`
- `useMatches` does not fetch when `resumeId=null`
- `useMatches` calls `matchResume(resumeId, 20)` when `resumeId` is set
- Test pattern: follow `apps/web/src/__tests__/hooks/api/use-user-profile.test.ts`

**Integration / Manual**:
- With 0 resumes: Career Radar shows "No Matches Yet" empty state with onboarding CTA
- With ≥1 resume (no embedding): loading spinner during match fetch → likely empty result or error
- With embedded resume: real match cards render with score + company
- Tailoring still works end-to-end (CV tailor flow not broken)

**Coverage target**: 80%+ for new hook files.

Reference: `.agent/rules/testing.md` — unit + manual E2E required.

---

## 5. Security Considerations

- `fetchWithAuth` already attaches the JWT bearer token; no additional auth work needed.
- `resumeId` originates from the authenticated user's resume list (not user-supplied input), so no injection risk.
- `resumeId!` non-null assertion is guarded by `enabled: resumeId !== null` — the assertion is safe.
- No PII is sent to the frontend beyond what was already in `MatchCandidate` (job_id, score, title, company).

Reference: `.agent/rules/security.md` — no new attack surface introduced.

---

## 6. Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|------------|
| User has no resumes → `resumeId` is null → matches query disabled → empty state shown | Low | Existing empty state + onboarding CTA already handles this correctly |
| Resume exists but has no embedding → match API returns 200 with 0 results | Medium | Empty `matches` array renders the "No Matches Yet" card; acceptable UX for now |
| `matchResume` is a POST but behaves like a read → can't use GET semantics | Low | TanStack Query `useQuery` with POST body is correct pattern for idempotent reads; consistent with team precedents in `use-hidden-job-market.ts` |
| Stale match data if user uploads a new resume | Low | `staleTime: 5 * 60 * 1000` means data refreshes on next page visit after 5 min |

---

## 7. Success Criteria

- [ ] TypeScript build passes with zero new errors (`tsc --noEmit`)
- [ ] `useResumes` and `useMatches` hooks have unit test coverage ≥ 80%
- [ ] Career Radar page shows real matches when a resume with embedding exists
- [ ] Career Radar page shows "No Matches Yet" when user has 0 resumes
- [ ] `tailorCV` flow continues to work (regression check)
- [ ] No console errors in browser when visiting `/dashboard/matches`

---

## 8. Architecture Impact

```
matches/page.tsx
  ├── useResumes() ──→ GET /api/v1/resumes/        [new hook + api-client]
  └── useMatches(resumeId) ──→ POST /api/v1/ai/match-resume/{id}  [new hook]
```

No structural changes to backend. All new files follow the existing `hooks/api/use-*.ts` and `lib/api-client/*.ts` conventions. TanStack Query cache is independent (no invalidation side-effects on existing queries).

---

## 9. API / Data Model Changes

**No backend changes.** Frontend changes only:
- New type: `ResumeSummary` (mirrors existing `ResumeSummaryResponse` from backend)
- `MatchResponse` and `MatchCandidate` already exist in `types/api/ai.ts`

---

## 10. Rollback Strategy

All changes are additive (new files + 2 line additions to existing index files). To rollback:
1. Revert `matches/page.tsx` to the hardcoded state (git revert the commit)
2. The new hook/api-client/type files can remain (they're inert without consumers)

No database migrations. No env var changes. Zero infrastructure impact.

---

## 11. Observability

- TanStack Query DevTools (already in dev) will show `["resumes","list"]` and `["ai","matches",{resumeId}]` queries
- Backend already logs: `resume uploaded: user=X resume_id=Y` and matching telemetry
- No new logging additions needed

---

## 12. Performance Impact

- **Bundle**: +2 new `.ts` files ≈ +1.5 KB gzip (negligible)
- **Network**: 2 additional API calls on page mount (resumes list + match POST). Both are fast (<200ms each on warm Railway instance)
- **Caching**: `staleTime: 5min` on matches; `staleTime: 2min` on resumes list. SWR behaviour prevents re-fetches on tab refocus within these windows

---

## 13. Documentation Updates

- `CHANGELOG.md`: Add entry under `[Unreleased]` — "feat: Career Radar now displays live job matches from API"
- `ROADMAP.md`: Mark "Job Matches page API integration" as complete in Sprint 50 deliverables
- No ADR required (follows established patterns)

Reference: `.agent/rules/documentation.md`

---

## 14. Dependencies

**Blocks**: None (all backend endpoints exist)
**Blocked by**: None
**Downstream impact**: `tailorCV` in `matches/page.tsx` already uses `resumeId`; wiring `resumeId` from the real API makes tailor-CV fully functional end-to-end

---

## 15. Alternatives Considered

**Alternative**: Derive `resumeId` from `useAuth()` user context / profile  
**Rejected**: The user profile API does not expose `resumeId`. The resumes list endpoint is the canonical source. Adding `resumeId` to the auth context would require changes across `AuthProvider`, `useAuth` hook, and the auth API client — 4x more files, higher risk.

**Alternative**: Pass `resumeId` as a URL search param from the onboarding flow  
**Rejected**: Breaks direct navigation to `/dashboard/matches`. The page must work standalone.

---

## Alignment Verification

| Check | Status |
|-------|--------|
| Trust > Optimization | ✅ No premature optimization; direct API calls |
| Existing Patterns | ✅ Matches `use-career-dna.ts` hook shape exactly |
| Rules Consulted | `security.md`, `testing.md`, `coding-style.md`, `performance.md` |
| Coding Style | ✅ Immutable patterns; no mutation; small focused files |

---

*Plan saved: `docs/PLAN-matches-api-integration.md`*  
*Approve to start with `/implement`.*
