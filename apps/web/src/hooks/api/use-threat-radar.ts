/**
 * PathForge — Hook: useThreatRadar
 * ===================================
 * Data-fetching hooks for Career Threat Radar™ endpoints.
 * Query hooks are auth-gated; mutations invalidate threat-radar domain.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { threatRadarApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  CareerResilienceResponse,
  SkillShieldMatrixResponse,
  ThreatAlertListResponse,
  ThreatAlertResponse,
  ThreatAlertUpdateRequest,
  ThreatRadarOverviewResponse,
  ThreatRadarScanResponse,
} from "@/types/api";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

/* ── Query Hooks ─────────────────────────────────────────── */

export function useThreatRadarOverview() {
  const { isAuthenticated } = useAuth();

  return useQuery<ThreatRadarOverviewResponse, ApiError>({
    queryKey: queryKeys.threatRadar.overview(),
    queryFn: () => threatRadarApi.getOverview(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useThreatRadarResilience() {
  const { isAuthenticated } = useAuth();

  return useQuery<CareerResilienceResponse, ApiError>({
    queryKey: queryKeys.threatRadar.resilience(),
    queryFn: () => threatRadarApi.getResilience(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useThreatRadarSkillsShield() {
  const { isAuthenticated } = useAuth();

  return useQuery<SkillShieldMatrixResponse, ApiError>({
    queryKey: queryKeys.threatRadar.skillsShield(),
    queryFn: () => threatRadarApi.getSkillsShield(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useThreatRadarAlerts(
  page: number = 1,
  pageSize: number = 20,
  alertStatus?: string,
) {
  const { isAuthenticated } = useAuth();

  return useQuery<ThreatAlertListResponse, ApiError>({
    queryKey: queryKeys.threatRadar.alerts(page, alertStatus),
    queryFn: () => threatRadarApi.getAlerts(page, pageSize, alertStatus),
    enabled: isAuthenticated,
    staleTime: 2 * 60 * 1000,
  });
}

/* ── Mutation Hooks ──────────────────────────────────────── */

export function useTriggerThreatScan() {
  const queryClient = useQueryClient();

  return useMutation<
    ThreatRadarScanResponse,
    ApiError,
    { socCode: string; industryName: string }
  >({
    mutationFn: ({ socCode, industryName }) =>
      threatRadarApi.triggerScan(socCode, industryName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.threatRadar.all });
    },
  });
}

export function useUpdateThreatAlert() {
  const queryClient = useQueryClient();

  return useMutation<
    ThreatAlertResponse,
    ApiError,
    { alertId: string; data: ThreatAlertUpdateRequest }
  >({
    mutationFn: ({ alertId, data }) =>
      threatRadarApi.updateAlert(alertId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.threatRadar.all });
    },
  });
}
