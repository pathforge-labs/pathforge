/**
 * PathForge — Career Resilience Score™ Trend Hook
 * ==================================================
 * Sprint 36 WS-5: Fetches historical resilience data for trend line.
 *
 * Endpoint: GET /api/v1/threat-radar/resilience/history?days=90
 * Returns: Array<{ date: string; score: number; delta: number }>
 */

"use client";

import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/lib/query-keys";
import { threatRadarApi } from "@/lib/api-client";
import type { ApiError } from "@/lib/http";
import type { ResilienceHistoryResponse } from "@/lib/api-client/threat-radar";
import { useAuth } from "@/hooks/use-auth";

// Re-export for consumer convenience
export type { ResilienceDataPoint, ResilienceHistoryResponse } from "@/lib/api-client/threat-radar";

// ── Hook ──────────────────────────────────────────────────────

/**
 * Fetch historical resilience score data.
 *
 * @param days - Number of days to fetch (default: 90, max: 365)
 */
export function useResilienceTrend(days: number = 90) {
  const { isAuthenticated } = useAuth();

  return useQuery<ResilienceHistoryResponse, ApiError>({
    queryKey: queryKeys.threatRadar.resilienceHistory(days),
    queryFn: () => threatRadarApi.getResilienceHistory(days),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchOnWindowFocus: false,
  });
}
