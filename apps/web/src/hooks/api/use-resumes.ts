"use client";

import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { resumesApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { ResumeSummary } from "@/types/api";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

/**
 * Fetch the current user's resume summaries.
 *
 * Explicit return type per the repository style guide — keeps the
 * hook's public shape stable even if TanStack Query widens or narrows
 * its overloads in future versions.
 *
 * ``enabled: isAuthenticated`` ensures the hook stays silent until the
 * auth provider has finished restoring a session, preventing a 401
 * flash on first render.
 */
export function useResumes(): UseQueryResult<ResumeSummary[], ApiError> {
  const { isAuthenticated } = useAuth();

  return useQuery<ResumeSummary[], ApiError>({
    queryKey: queryKeys.resumes.list(),
    queryFn: () => resumesApi.list(),
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000,
  });
}
