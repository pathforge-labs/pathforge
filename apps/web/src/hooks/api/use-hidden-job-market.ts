"use client";

/**
 * PathForge — Hooks: Hidden Job Market Detector™
 * ================================================
 * TanStack Query hooks for signals, outreach, and opportunities.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { hiddenJobMarketApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  CompanySignalResponse,
  DismissSignalRequest,
  GenerateOutreachRequest,
  HiddenJobMarketDashboardResponse,
  HiddenJobMarketPreferenceUpdateRequest,
  HiddenJobMarketPreferenceResponse,
  OpportunityRadarResponse,
  OutreachTemplateResponse,
  ScanCompanyRequest,
  ScanIndustryRequest,
  SignalCompareRequest,
  SignalComparisonResponse,
} from "@/types/api";
import type { MessageResponse } from "@/types/api/common";

const STALE_5M = 5 * 60 * 1000;

// ── Queries ─────────────────────────────────────────────────

export function useHiddenJobMarketDashboard(): ReturnType<typeof useQuery<HiddenJobMarketDashboardResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.hiddenJobMarket.dashboard(),
    queryFn: () => hiddenJobMarketApi.getDashboard(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useHiddenJobMarketSignal(signalId: string): ReturnType<typeof useQuery<CompanySignalResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.hiddenJobMarket.signal(signalId),
    queryFn: () => hiddenJobMarketApi.getSignal(signalId),
    enabled: isAuthenticated && !!signalId,
    staleTime: STALE_5M,
  });
}

export function useOpportunities(): ReturnType<typeof useQuery<OpportunityRadarResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.hiddenJobMarket.opportunities(),
    queryFn: () => hiddenJobMarketApi.getOpportunities(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useHiddenJobMarketPreferences(): ReturnType<typeof useQuery<HiddenJobMarketPreferenceResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.hiddenJobMarket.preferences(),
    queryFn: () => hiddenJobMarketApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

// ── Mutations ───────────────────────────────────────────────

export function useScanCompany(): ReturnType<typeof useMutation<CompanySignalResponse, Error, ScanCompanyRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ScanCompanyRequest) => hiddenJobMarketApi.scanCompany(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.hiddenJobMarket.all });
    },
  });
}

export function useScanIndustry(): ReturnType<typeof useMutation<CompanySignalResponse[], Error, ScanIndustryRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: ScanIndustryRequest) => hiddenJobMarketApi.scanIndustry(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.hiddenJobMarket.all });
    },
  });
}

export function useCompareSignals(): ReturnType<typeof useMutation<SignalComparisonResponse, Error, SignalCompareRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: SignalCompareRequest) => hiddenJobMarketApi.compareSignals(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.hiddenJobMarket.all });
    },
  });
}

export function useSurfaceOpportunities(): ReturnType<typeof useMutation<OpportunityRadarResponse, Error, void>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => hiddenJobMarketApi.surfaceOpportunities(),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.hiddenJobMarket.opportunities() });
    },
  });
}

interface GenerateOutreachParams {
  readonly signalId: string;
  readonly data: GenerateOutreachRequest;
}

export function useGenerateOutreach(): ReturnType<typeof useMutation<OutreachTemplateResponse, Error, GenerateOutreachParams>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ signalId, data }: GenerateOutreachParams) => hiddenJobMarketApi.generateOutreach(signalId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.hiddenJobMarket.all });
    },
  });
}

interface DismissSignalParams {
  readonly signalId: string;
  readonly data: DismissSignalRequest;
}

export function useDismissSignal(): ReturnType<typeof useMutation<MessageResponse, Error, DismissSignalParams>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ signalId, data }: DismissSignalParams) => hiddenJobMarketApi.dismissSignal(signalId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.hiddenJobMarket.all });
    },
  });
}

export function useUpdateHiddenJobMarketPreferences(): ReturnType<typeof useMutation<HiddenJobMarketPreferenceResponse, Error, HiddenJobMarketPreferenceUpdateRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: HiddenJobMarketPreferenceUpdateRequest) => hiddenJobMarketApi.updatePreferences(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.hiddenJobMarket.preferences() });
    },
  });
}
