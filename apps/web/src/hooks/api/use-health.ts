/**
 * PathForge — Hook: useHealthCheck
 * ===================================
 * Polls the backend readiness endpoint every 30 seconds.
 */

"use client";

import { useQuery } from "@tanstack/react-query";

import { healthApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { ReadinessCheckResponse } from "@/types/api";

export function useHealthCheck() {
  return useQuery<ReadinessCheckResponse>({
    queryKey: queryKeys.health.ready(),
    queryFn: () => healthApi.ready(),
    refetchInterval: 30_000,
    staleTime: 30_000,
    gcTime: 60_000,
    retry: 1,
    refetchOnWindowFocus: false,
  });
}
