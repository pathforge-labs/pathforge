/**
 * PathForge — Hook: useCommandCenter
 * =====================================
 * Data-fetching hooks for the Career Command Center™.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { commandCenterApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  CommandCenterDashboardResponse,
  CareerHealthSummaryResponse,
  EngineDetailResponse,
  VitalsSnapshotResponse,
} from "@/types/api";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

export function useCommandCenterDashboard() {
  const { isAuthenticated } = useAuth();

  return useQuery<CommandCenterDashboardResponse, ApiError>({
    queryKey: queryKeys.commandCenter.dashboard(),
    queryFn: () => commandCenterApi.getDashboard(),
    enabled: isAuthenticated,
    staleTime: 60_000,
    gcTime: 5 * 60 * 1000,
  });
}

export function useCareerHealthSummary() {
  const { isAuthenticated } = useAuth();

  return useQuery<CareerHealthSummaryResponse, ApiError>({
    queryKey: queryKeys.commandCenter.healthSummary(),
    queryFn: () => commandCenterApi.getHealthSummary(),
    enabled: isAuthenticated,
    staleTime: 60_000,
  });
}

export function useEngineDetail(engineName: string) {
  const { isAuthenticated } = useAuth();

  return useQuery<EngineDetailResponse, ApiError>({
    queryKey: queryKeys.commandCenter.engine(engineName),
    queryFn: () => commandCenterApi.getEngineDetail(engineName),
    enabled: isAuthenticated && Boolean(engineName),
    staleTime: 60_000,
  });
}

export function useRefreshVitals() {
  const queryClient = useQueryClient();

  return useMutation<VitalsSnapshotResponse, ApiError>({
    mutationFn: () => commandCenterApi.refreshSnapshot(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.commandCenter.all });
    },
  });
}

export function useCommandCenterPreferences() {
  const { isAuthenticated } = useAuth();

  return useQuery({
    queryKey: queryKeys.commandCenter.preferences(),
    queryFn: () => commandCenterApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useUpdateCommandCenterPreferences() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: Record<string, unknown>) => commandCenterApi.updatePreferences(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.commandCenter.preferences() });
    },
  });
}
