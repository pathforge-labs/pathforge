/**
 * PathForge — Hook: useAiUsage (T4 / Sprint 56, ADR-0008)
 * =========================================================
 *
 * React Query hook for the Transparent AI Accounting summary
 * endpoint.
 */

"use client";

import { useQuery } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { aiUsageApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { UsageSummaryAiResponse } from "@/types/api";

/**
 * Returns the authenticated user's AI usage summary for the period.
 *
 * Stale time: 5 minutes — usage figures don't change faster than a
 * user can refresh, and the underlying server query is cheap (single
 * indexed SELECT) so on-demand refetch is fine.
 *
 * Auth-gated via the `enabled` option (Style Guide §92): the query
 * does not fire until the user is authenticated, so the hook is safe
 * to mount on a public-shell layout that resolves auth asynchronously.
 */
export function useAiUsageSummary(
  period: "current_month" = "current_month",
) {
  const { isAuthenticated } = useAuth();
  return useQuery<UsageSummaryAiResponse>({
    queryKey: queryKeys.aiUsage.summary(period),
    queryFn: () => aiUsageApi.getSummary(period),
    staleTime: 5 * 60 * 1000,
    enabled: isAuthenticated,
  });
}
