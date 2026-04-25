"use client";

/**
 * PathForge — Hooks: Salary Intelligence Engine™
 * =================================================
 * TanStack Query hooks for the Salary Intelligence dashboard.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { salaryIntelligenceApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  SalaryDashboardResponse,
  SalaryScanResponse,
  SalaryEstimateResponse,
  SalaryImpactAnalysisResponse,
  SalaryHistoryEntryResponse,
  SalaryScenarioResponse,
  SalaryScenarioRequest,
  SalaryPreferenceResponse,
  SalaryPreferenceUpdateRequest,
} from "@/types/api";

const STALE_5M = 5 * 60 * 1000;

// ── Queries ─────────────────────────────────────────────────

export function useSalaryDashboard(): ReturnType<typeof useQuery<SalaryDashboardResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.salaryIntelligence.dashboard(),
    queryFn: () => salaryIntelligenceApi.getDashboard(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useSalaryEstimate(): ReturnType<typeof useQuery<SalaryEstimateResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.salaryIntelligence.estimate(),
    queryFn: () => salaryIntelligenceApi.getEstimate(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useSalarySkillImpacts(): ReturnType<typeof useQuery<SalaryImpactAnalysisResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.salaryIntelligence.skillImpacts(),
    queryFn: () => salaryIntelligenceApi.getSkillImpacts(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useSalaryTrajectory(): ReturnType<typeof useQuery<SalaryHistoryEntryResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.salaryIntelligence.trajectory(),
    queryFn: () => salaryIntelligenceApi.getTrajectory(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useSalaryScenarios(): ReturnType<typeof useQuery<SalaryScenarioResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.salaryIntelligence.scenarios(),
    queryFn: () => salaryIntelligenceApi.listScenarios(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useSalaryPreferences(): ReturnType<typeof useQuery<SalaryPreferenceResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.salaryIntelligence.preferences(),
    queryFn: () => salaryIntelligenceApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

// ── Mutations ───────────────────────────────────────────────

export function useTriggerSalaryScan(): ReturnType<typeof useMutation<SalaryScanResponse, Error, void>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => salaryIntelligenceApi.triggerScan(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.salaryIntelligence.all });
    },
  });
}

export function useRunSalaryScenario(): ReturnType<typeof useMutation<SalaryScenarioResponse, Error, SalaryScenarioRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SalaryScenarioRequest) => salaryIntelligenceApi.runScenario(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.salaryIntelligence.scenarios() });
    },
  });
}

export function useUpdateSalaryPreferences(): ReturnType<typeof useMutation<SalaryPreferenceResponse, Error, SalaryPreferenceUpdateRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SalaryPreferenceUpdateRequest) => salaryIntelligenceApi.updatePreferences(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.salaryIntelligence.preferences() });
    },
  });
}
