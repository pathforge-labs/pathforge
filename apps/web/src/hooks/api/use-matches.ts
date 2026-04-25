"use client";

import { useQuery, skipToken, type UseQueryResult } from "@tanstack/react-query";

import { matchResume } from "@/lib/api-client/ai";
import { queryKeys } from "@/lib/query-keys";
import type { MatchResponse } from "@/types/api/ai";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

/**
 * Fetch job matches for a given resume.
 *
 * Explicit return type is required by the repository style guide
 * ("Explicit return types on all exported functions") and prevents
 * the ``useQuery`` overload from widening ``data`` to ``unknown`` when
 * the hook is imported in typescript-strict consumers.
 *
 * Gated on both authentication and a non-null ``resumeId``:
 * ``skipToken`` keeps the query disabled and the cache untouched until
 * a concrete resume is selected, avoiding a spurious 401 request on
 * logout/session-restore.
 */
export function useMatches(
  resumeId: string | null,
): UseQueryResult<MatchResponse, ApiError> {
  const { isAuthenticated } = useAuth();

  return useQuery<MatchResponse, ApiError>({
    queryKey: queryKeys.ai.matches(resumeId),
    queryFn:
      isAuthenticated && resumeId !== null
        ? () => matchResume(resumeId, 20)
        : skipToken,
    staleTime: 5 * 60 * 1000,
  });
}
