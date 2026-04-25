"use client";

/**
 * PathForge — Hooks: Interview Intelligence™
 * ============================================
 * TanStack Query hooks for interview preparation, questions, STAR, and negotiation.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useAuth } from "@/hooks/use-auth";
import { interviewIntelligenceApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type {
  GenerateNegotiationScriptRequest,
  GenerateQuestionsRequest,
  GenerateSTARExamplesRequest,
  InterviewDashboardResponse,
  InterviewPreferenceResponse,
  InterviewPreferenceUpdateRequest,
  InterviewPrepCompareRequest,
  InterviewPrepComparisonResponse,
  InterviewPrepRequest,
  InterviewPrepResponse,
  InterviewQuestionResponse,
  NegotiationScriptResponse,
  STARExampleResponse,
} from "@/types/api";

const STALE_5M = 5 * 60 * 1000;

// ── Queries ─────────────────────────────────────────────────

export function useInterviewDashboard(): ReturnType<typeof useQuery<InterviewDashboardResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.interviewIntelligence.dashboard(),
    queryFn: () => interviewIntelligenceApi.getDashboard(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

export function useInterviewPrep(prepId: string): ReturnType<typeof useQuery<InterviewPrepResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.interviewIntelligence.prep(prepId),
    queryFn: () => interviewIntelligenceApi.getPrep(prepId),
    enabled: isAuthenticated && !!prepId,
    staleTime: STALE_5M,
  });
}

export function useInterviewPreferences(): ReturnType<typeof useQuery<InterviewPreferenceResponse>> {
  const { isAuthenticated } = useAuth();
  return useQuery({
    queryKey: queryKeys.interviewIntelligence.preferences(),
    queryFn: () => interviewIntelligenceApi.getPreferences(),
    enabled: isAuthenticated,
    staleTime: STALE_5M,
  });
}

// ── Mutations ───────────────────────────────────────────────

export function useCreateInterviewPrep(): ReturnType<typeof useMutation<InterviewPrepResponse, Error, InterviewPrepRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InterviewPrepRequest) => interviewIntelligenceApi.createPrep(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.interviewIntelligence.all });
    },
  });
}

export function useDeleteInterviewPrep(): ReturnType<typeof useMutation<void, Error, string>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (prepId: string) => interviewIntelligenceApi.deletePrep(prepId),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.interviewIntelligence.all });
    },
  });
}

export function useCompareInterviewPreps(): ReturnType<typeof useMutation<InterviewPrepComparisonResponse, Error, InterviewPrepCompareRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InterviewPrepCompareRequest) => interviewIntelligenceApi.comparePreps(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.interviewIntelligence.all });
    },
  });
}

interface GenerateQuestionsParams {
  readonly prepId: string;
  readonly data: GenerateQuestionsRequest;
}

export function useGenerateQuestions(): ReturnType<typeof useMutation<InterviewQuestionResponse[], Error, GenerateQuestionsParams>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ prepId, data }: GenerateQuestionsParams) => interviewIntelligenceApi.generateQuestions(prepId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.interviewIntelligence.all });
    },
  });
}

interface GenerateStarParams {
  readonly prepId: string;
  readonly data: GenerateSTARExamplesRequest;
}

export function useGenerateStarExamples(): ReturnType<typeof useMutation<STARExampleResponse[], Error, GenerateStarParams>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ prepId, data }: GenerateStarParams) => interviewIntelligenceApi.generateStarExamples(prepId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.interviewIntelligence.all });
    },
  });
}

interface GenerateNegotiationParams {
  readonly prepId: string;
  readonly data: GenerateNegotiationScriptRequest;
}

export function useGenerateNegotiationScript(): ReturnType<typeof useMutation<NegotiationScriptResponse, Error, GenerateNegotiationParams>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ prepId, data }: GenerateNegotiationParams) => interviewIntelligenceApi.generateNegotiationScript(prepId, data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.interviewIntelligence.all });
    },
  });
}

export function useUpdateInterviewPreferences(): ReturnType<typeof useMutation<InterviewPreferenceResponse, Error, InterviewPreferenceUpdateRequest>> {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: InterviewPreferenceUpdateRequest) => interviewIntelligenceApi.updatePreferences(data),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: queryKeys.interviewIntelligence.preferences() });
    },
  });
}
