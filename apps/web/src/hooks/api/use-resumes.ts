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
