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
