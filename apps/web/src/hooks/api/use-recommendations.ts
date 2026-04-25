"use client";

/**
 * PathForge — Hooks: Cross-Engine Recommendation Intelligence™
 * ==============================================================
 * TanStack Query hooks for recommendations, priority scoring, and workflows.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { recommendationApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  CrossEngineRecommendationResponse,
  GenerateRecommendationsRequest,
  RecommendationBatchResponse,
  RecommendationCorrelationResponse,
  RecommendationDashboardResponse,
  RecommendationListResponse,
  RecommendationPreferenceResponse,
  RecommendationPreferenceUpdate,
  UpdateRecommendationStatusRequest,
} from "@/types/api";

const STALE_5M = 5 * 60 * 1000;

// ── Queries ─────────────────────────────────────────────────

export function useRecommendationDashboard(): ReturnType<typeof useQuery<RecommendationDashboardResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.recommendations.dashboard(),
    queryFn: () => recommendationApi.getDashboard(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useRecommendations(
  status?: string,
  sortBy?: string,
  limit?: number,
  offset?: number,
): ReturnType<typeof useQuery<RecommendationListResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.recommendations.list({ status, sortBy, limit, offset }),
    queryFn: () => recommendationApi.listRecommendations(status, sortBy, limit, offset),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useRecommendationDetail(recommendationId: string): ReturnType<typeof useQuery<CrossEngineRecommendationResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.recommendations.detail(recommendationId),
    queryFn: () => recommendationApi.getRecommendationDetail(recommendationId),
    enabled: isAuthenticated && !!recommendationId,
    staleTime: STALE_5M,
  });
}

export function useRecommendationCorrelations(recommendationId: string): ReturnType<typeof useQuery<RecommendationCorrelationResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.recommendations.correlations(recommendationId),
    queryFn: () => recommendationApi.getCorrelations(recommendationId),
    enabled: isAuthenticated && !!recommendationId,
    staleTime: STALE_5M,
  });
}

export function useRecommendationBatches(): ReturnType<typeof useQuery<RecommendationBatchResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.recommendations.batches(),
    queryFn: () => recommendationApi.listBatches(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useRecommendationPreferences(): ReturnType<typeof useQuery<RecommendationPreferenceResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.recommendations.preferences(),
    queryFn: () => recommendationApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

// ── Mutations ───────────────────────────────────────────────

export function useGenerateRecommendations(): ReturnType<typeof useMutation<RecommendationBatchResponse, Error, GenerateRecommendationsRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: GenerateRecommendationsRequest) => recommendationApi.generateRecommendations(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recommendations.all });
    },
  });
}

interface UpdateStatusParams {
  readonly recommendationId: string;
  readonly data: UpdateRecommendationStatusRequest;
}

export function useUpdateRecommendationStatus(): ReturnType<typeof useMutation<CrossEngineRecommendationResponse, Error, UpdateStatusParams>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ recommendationId, data }: UpdateStatusParams) => recommendationApi.updateRecommendationStatus(recommendationId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recommendations.all });
    },
  });
}

export function useUpdateRecommendationPreferences(): ReturnType<typeof useMutation<RecommendationPreferenceResponse, Error, RecommendationPreferenceUpdate>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RecommendationPreferenceUpdate) => recommendationApi.updatePreferences(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.recommendations.preferences() });
    },
  });
}
