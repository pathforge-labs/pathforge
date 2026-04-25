"use client";

/**
 * PathForge — Hooks: Career Simulation Engine™
 * ===============================================
 * TanStack Query hooks for the Career Simulator dashboard.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { careerSimulationApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  SimulationDashboardResponse,
  CareerSimulationResponse,
  SimulationComparisonResponse,
  SimulationPreferenceResponse,
  SimulationPreferenceUpdateRequest,
  RoleTransitionSimRequest,
  GeoMoveSimRequest,
  SkillInvestmentSimRequest,
  IndustryPivotSimRequest,
  SeniorityJumpSimRequest,
  SimulationCompareRequest,
} from "@/types/api";

const STALE_5M = 5 * 60 * 1000;

// ── Queries ─────────────────────────────────────────────────

export function useSimulationDashboard(page: number = 1): ReturnType<typeof useQuery<SimulationDashboardResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.careerSimulation.dashboard(page),
    queryFn: () => careerSimulationApi.getDashboard(page),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useSimulationDetail(simulationId: string): ReturnType<typeof useQuery<CareerSimulationResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.careerSimulation.detail(simulationId),
    queryFn: () => careerSimulationApi.getSimulation(simulationId),
    enabled: isAuthenticated && simulationId.length > 0,
    staleTime: STALE_5M,
  });
}

export function useSimulationPreferences(): ReturnType<typeof useQuery<SimulationPreferenceResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.careerSimulation.preferences(),
    queryFn: () => careerSimulationApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

// ── Scenario Mutations ──────────────────────────────────────

export function useSimulateRole(): ReturnType<typeof useMutation<CareerSimulationResponse, Error, RoleTransitionSimRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: RoleTransitionSimRequest) => careerSimulationApi.simulateRole(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerSimulation.all });
    },
  });
}

export function useSimulateGeo(): ReturnType<typeof useMutation<CareerSimulationResponse, Error, GeoMoveSimRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: GeoMoveSimRequest) => careerSimulationApi.simulateGeo(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerSimulation.all });
    },
  });
}

export function useSimulateSkill(): ReturnType<typeof useMutation<CareerSimulationResponse, Error, SkillInvestmentSimRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SkillInvestmentSimRequest) => careerSimulationApi.simulateSkill(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerSimulation.all });
    },
  });
}

export function useSimulateIndustry(): ReturnType<typeof useMutation<CareerSimulationResponse, Error, IndustryPivotSimRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: IndustryPivotSimRequest) => careerSimulationApi.simulateIndustry(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerSimulation.all });
    },
  });
}

export function useSimulateSeniority(): ReturnType<typeof useMutation<CareerSimulationResponse, Error, SeniorityJumpSimRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SeniorityJumpSimRequest) => careerSimulationApi.simulateSeniority(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerSimulation.all });
    },
  });
}

// ── Compare & Delete ────────────────────────────────────────

export function useCompareSimulations(): ReturnType<typeof useMutation<SimulationComparisonResponse, Error, SimulationCompareRequest>> {
  return useMutation({
    mutationFn: (data: SimulationCompareRequest) => careerSimulationApi.compare(data),
  });
}

export function useDeleteSimulation(): ReturnType<typeof useMutation<void, Error, string>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (simulationId: string) => careerSimulationApi.deleteSimulation(simulationId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerSimulation.all });
    },
  });
}

// ── Preferences Mutation ────────────────────────────────────

export function useUpdateSimulationPreferences(): ReturnType<typeof useMutation<SimulationPreferenceResponse, Error, SimulationPreferenceUpdateRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SimulationPreferenceUpdateRequest) => careerSimulationApi.updatePreferences(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerSimulation.preferences() });
    },
  });
}
