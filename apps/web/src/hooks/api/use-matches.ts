"use client";

import { useQuery, skipToken } from "@tanstack/react-query";

import { matchResume } from "@/lib/api-client/ai";
import { queryKeys } from "@/lib/query-keys";
import type { MatchResponse } from "@/types/api/ai";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

export function useMatches(resumeId: string | null) {
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
