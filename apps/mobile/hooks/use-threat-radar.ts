/**
 * PathForge Mobile — Hook: use-threat-radar
 * ============================================
 * TanStack Query hook for Threat Radar overview data.
 */

import { useQuery } from "@tanstack/react-query";

import { getThreatRadarOverview } from "../lib/api-client/threat-radar";
import { QUERY_STALE_TIME_MS } from "../constants/config";

import type { ThreatRadarOverviewResponse } from "@pathforge/shared/types/api/threat-radar";

// ── Query Keys ──────────────────────────────────────────────

export const THREAT_RADAR_KEYS = {
  all: ["threat-radar"] as const,
  overview: () => [...THREAT_RADAR_KEYS.all, "overview"] as const,
} as const;

// ── Hook ────────────────────────────────────────────────────

export function useThreatRadarOverview(): ReturnType<typeof useQuery<ThreatRadarOverviewResponse>> {
  return useQuery<ThreatRadarOverviewResponse>({
    queryKey: THREAT_RADAR_KEYS.overview(),
    queryFn: getThreatRadarOverview,
    staleTime: QUERY_STALE_TIME_MS,
  });
}
