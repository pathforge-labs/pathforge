"use client";

/**
 * PathForge — Hooks: Transition Pathways
 * ========================================
 * TanStack Query hooks for the Career Moves dashboard.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { transitionPathwaysApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  TransitionDashboardResponse,
  TransitionScanResponse,
  TransitionPathResponse,
  TransitionSummaryResponse,
  SkillBridgeEntryResponse,
  TransitionMilestoneResponse,
  TransitionExploreRequest,
  RoleWhatIfRequest,
  TransitionPreferenceResponse,
  TransitionPreferenceUpdateRequest,
} from "@/types/api";

const STALE_5M = 5 * 60 * 1000;

// ── Queries ─────────────────────────────────────────────────

export function useTransitionDashboard(): ReturnType<typeof useQuery<TransitionDashboardResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.transitionPathways.dashboard(),
    queryFn: () => transitionPathwaysApi.getDashboard(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useTransitionList(): ReturnType<typeof useQuery<TransitionSummaryResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.transitionPathways.list(),
    queryFn: () => transitionPathwaysApi.list(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useTransitionDetail(transitionId: string): ReturnType<typeof useQuery<TransitionPathResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.transitionPathways.detail(transitionId),
    queryFn: () => transitionPathwaysApi.getTransition(transitionId),
    enabled: isAuthenticated && transitionId.length > 0,
    staleTime: STALE_5M,
  });
}

export function useTransitionSkillBridge(transitionId: string): ReturnType<typeof useQuery<SkillBridgeEntryResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.transitionPathways.skillBridge(transitionId),
    queryFn: () => transitionPathwaysApi.getSkillBridge(transitionId),
    enabled: isAuthenticated && transitionId.length > 0,
    staleTime: STALE_5M,
  });
}

export function useTransitionMilestones(transitionId: string): ReturnType<typeof useQuery<TransitionMilestoneResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.transitionPathways.milestones(transitionId),
    queryFn: () => transitionPathwaysApi.getMilestones(transitionId),
    enabled: isAuthenticated && transitionId.length > 0,
    staleTime: STALE_5M,
  });
}

export function useTransitionPreferences(): ReturnType<typeof useQuery<TransitionPreferenceResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.transitionPathways.preferences(),
    queryFn: () => transitionPathwaysApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

// ── Mutations ───────────────────────────────────────────────

export function useExploreTransition(): ReturnType<typeof useMutation<TransitionScanResponse, Error, TransitionExploreRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TransitionExploreRequest) => transitionPathwaysApi.explore(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.transitionPathways.all });
    },
  });
}

export function useTransitionWhatIf(): ReturnType<typeof useMutation<TransitionPathResponse, Error, RoleWhatIfRequest>> {
  return useMutation({
    mutationFn: (data: RoleWhatIfRequest) => transitionPathwaysApi.whatIf(data),
  });
}

export function useDeleteTransition(): ReturnType<typeof useMutation<void, Error, string>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (transitionId: string) => transitionPathwaysApi.deleteTransition(transitionId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.transitionPathways.all });
    },
  });
}

export function useUpdateTransitionPreferences(): ReturnType<typeof useMutation<TransitionPreferenceResponse, Error, TransitionPreferenceUpdateRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: TransitionPreferenceUpdateRequest) => transitionPathwaysApi.updatePreferences(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.transitionPathways.preferences() });
    },
  });
}
