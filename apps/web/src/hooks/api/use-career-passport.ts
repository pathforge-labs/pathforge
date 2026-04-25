"use client";

/**
 * PathForge — Hooks: Cross-Border Career Passport™
 * ==================================================
 * TanStack Query hooks for credential mapping, country comparison, and visa assessment.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { careerPassportApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  CareerPassportDashboardResponse,
  CareerPassportPreferenceResponse,
  CareerPassportPreferenceUpdate,
  CountryComparisonRequest,
  CountryComparisonResponse,
  CredentialMappingRequest,
  CredentialMappingResponse,
  MarketDemandResponse,
  MultiCountryComparisonRequest,
  MultiCountryComparisonResponse,
  PassportScanResponse,
  VisaAssessmentRequest,
  VisaAssessmentResponse,
} from "@/types/api";

const STALE_5M = 5 * 60 * 1000;

// ── Queries ─────────────────────────────────────────────────

export function useCareerPassportDashboard(): ReturnType<typeof useQuery<CareerPassportDashboardResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.careerPassport.dashboard(),
    queryFn: () => careerPassportApi.getDashboard(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useMarketDemand(country: string): ReturnType<typeof useQuery<MarketDemandResponse[]>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.careerPassport.marketDemand(country),
    queryFn: () => careerPassportApi.getMarketDemand(country),
    enabled: isAuthenticated && !!country,
    staleTime: STALE_5M,
  });
}

export function useCareerPassportPreferences(): ReturnType<typeof useQuery<CareerPassportPreferenceResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.careerPassport.preferences(),
    queryFn: () => careerPassportApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

// ── Mutations ───────────────────────────────────────────────

interface FullScanParams {
  readonly data: CredentialMappingRequest;
  readonly nationality?: string;
}

export function useFullPassportScan(): ReturnType<typeof useMutation<PassportScanResponse, Error, FullScanParams>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ data, nationality }: FullScanParams) => careerPassportApi.fullScan(data, nationality),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerPassport.all });
    },
  });
}

export function useCreateCredentialMapping(): ReturnType<typeof useMutation<CredentialMappingResponse, Error, CredentialMappingRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CredentialMappingRequest) => careerPassportApi.createCredentialMapping(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerPassport.all });
    },
  });
}

export function useDeleteCredentialMapping(): ReturnType<typeof useMutation<void, Error, string>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (mappingId: string) => careerPassportApi.deleteCredentialMapping(mappingId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerPassport.all });
    },
  });
}

export function useCreateCountryComparison(): ReturnType<typeof useMutation<CountryComparisonResponse, Error, CountryComparisonRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CountryComparisonRequest) => careerPassportApi.createCountryComparison(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerPassport.all });
    },
  });
}

export function useMultiCountryComparison(): ReturnType<typeof useMutation<MultiCountryComparisonResponse, Error, MultiCountryComparisonRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: MultiCountryComparisonRequest) => careerPassportApi.multiCountryComparison(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerPassport.all });
    },
  });
}

export function useCreateVisaAssessment(): ReturnType<typeof useMutation<VisaAssessmentResponse, Error, VisaAssessmentRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: VisaAssessmentRequest) => careerPassportApi.createVisaAssessment(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerPassport.all });
    },
  });
}

export function useUpdateCareerPassportPreferences(): ReturnType<typeof useMutation<CareerPassportPreferenceResponse, Error, CareerPassportPreferenceUpdate>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: CareerPassportPreferenceUpdate) => careerPassportApi.updatePreferences(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.careerPassport.preferences() });
    },
  });
}
