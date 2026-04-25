"use client";

/**
 * PathForge — Hooks: Skill Decay & Growth Tracker
 * ==================================================
 * TanStack Query hooks for the Skills Health dashboard.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { skillDecayApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  SkillDecayDashboardResponse,
  SkillDecayScanResponse,
  SkillFreshnessResponse,
  SkillVelocityEntryResponse,
  ReskillingPathwayResponse,
  SkillRefreshRequest,
  SkillDecayPreferenceResponse,
  SkillDecayPreferenceUpdateRequest,
} from "@/types/api";

const STALE_5M = 5 * 60 * 1000;

// ── Queries ─────────────────────────────────────────────────

export function useSkillDecayDashboard(): ReturnType<typeof useQuery<SkillDecayDashboardResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.skillDecay.dashboard(),
    queryFn: () => skillDecayApi.getDashboard(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useSkillFreshness(): ReturnType<typeof useQuery<SkillFreshnessResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.skillDecay.freshness(),
    queryFn: () => skillDecayApi.getFreshness(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useSkillVelocityMap(): ReturnType<typeof useQuery<SkillVelocityEntryResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.skillDecay.velocityMap(),
    queryFn: () => skillDecayApi.getVelocityMap(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useReskillingPathways(): ReturnType<typeof useQuery<ReskillingPathwayResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.skillDecay.reskillingPathways(),
    queryFn: () => skillDecayApi.getReskillingPathways(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useSkillDecayPreferences(): ReturnType<typeof useQuery<SkillDecayPreferenceResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.skillDecay.preferences(),
    queryFn: () => skillDecayApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

// ── Mutations ───────────────────────────────────────────────

export function useTriggerDecayScan(): ReturnType<typeof useMutation<SkillDecayScanResponse, Error, void>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => skillDecayApi.triggerScan(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.skillDecay.all });
    },
  });
}

export function useRefreshSkill(): ReturnType<typeof useMutation<SkillFreshnessResponse, Error, SkillRefreshRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillRefreshRequest) => skillDecayApi.refreshSkill(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.skillDecay.all });
    },
  });
}

export function useUpdateSkillDecayPreferences(): ReturnType<typeof useMutation<SkillDecayPreferenceResponse, Error, SkillDecayPreferenceUpdateRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillDecayPreferenceUpdateRequest) => skillDecayApi.updatePreferences(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.skillDecay.preferences() });
    },
  });
}
