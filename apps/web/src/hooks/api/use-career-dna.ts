/**
 * PathForge — Hook: useCareerDna
 * =================================
 * Data-fetching hooks for Career DNA™ endpoints.
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { careerDnaApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  CareerDnaGenerateRequest,
  CareerDnaProfileResponse,
  CareerDnaSummaryResponse,
  ExperienceBlueprintResponse,
  GrowthVectorResponse,
  MarketPositionResponse,
  SkillGenomeEntryResponse,
  ValuesProfileResponse,
} from "@/types/api";
import type { ApiError } from "@/lib/http";
import { useAuth } from "@/hooks/use-auth";

export function useCareerDnaProfile() {
  const { isAuthenticated } = useAuth();

  return useQuery<CareerDnaProfileResponse, ApiError>({
    queryKey: queryKeys.careerDna.profile(),
    queryFn: () => careerDnaApi.getProfile(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useCareerDnaSummary() {
  const { isAuthenticated } = useAuth();

  return useQuery<CareerDnaSummaryResponse, ApiError>({
    queryKey: queryKeys.careerDna.summary(),
    queryFn: () => careerDnaApi.getSummary(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useGenerateCareerDna() {
  const queryClient = useQueryClient();

  return useMutation<CareerDnaProfileResponse, ApiError, CareerDnaGenerateRequest | undefined>({
    mutationFn: (params) => careerDnaApi.generate(params),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.careerDna.all });
      queryClient.invalidateQueries({ queryKey: queryKeys.commandCenter.all });
    },
  });
}

/* ── Dimension Hooks (for Radar Chart) ───────────────────── */

export function useSkillGenome() {
  const { isAuthenticated } = useAuth();

  return useQuery<SkillGenomeEntryResponse[], ApiError>({
    queryKey: queryKeys.careerDna.skillGenome(),
    queryFn: () => careerDnaApi.getSkillGenome(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useExperienceBlueprint() {
  const { isAuthenticated } = useAuth();

  return useQuery<ExperienceBlueprintResponse, ApiError>({
    queryKey: queryKeys.careerDna.experienceBlueprint(),
    queryFn: () => careerDnaApi.getExperienceBlueprint(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useGrowthVector() {
  const { isAuthenticated } = useAuth();

  return useQuery<GrowthVectorResponse, ApiError>({
    queryKey: queryKeys.careerDna.growthVector(),
    queryFn: () => careerDnaApi.getGrowthVector(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useValuesProfile() {
  const { isAuthenticated } = useAuth();

  return useQuery<ValuesProfileResponse, ApiError>({
    queryKey: queryKeys.careerDna.valuesProfile(),
    queryFn: () => careerDnaApi.getValuesProfile(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}

export function useMarketPosition() {
  const { isAuthenticated } = useAuth();

  return useQuery<MarketPositionResponse, ApiError>({
    queryKey: queryKeys.careerDna.marketPosition(),
    queryFn: () => careerDnaApi.getMarketPosition(),
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000,
  });
}
