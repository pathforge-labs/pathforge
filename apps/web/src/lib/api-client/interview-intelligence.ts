/**
 * PathForge — API Client: Interview Intelligence™
 * ================================================
 * Interview preparation, questions, STAR examples, and negotiation scripts.
 */

import { del, get, post, put } from "@/lib/http";
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

const BASE = "/api/v1/interview-intelligence";

export const interviewIntelligenceApi = {
  getDashboard: (): Promise<InterviewDashboardResponse> =>
    get<InterviewDashboardResponse>(`${BASE}/dashboard`),

  createPrep: (data: InterviewPrepRequest): Promise<InterviewPrepResponse> =>
    post<InterviewPrepResponse>(BASE, data),

  comparePreps: (data: InterviewPrepCompareRequest): Promise<InterviewPrepComparisonResponse> =>
    post<InterviewPrepComparisonResponse>(`${BASE}/compare`, data),

  getPreferences: (): Promise<InterviewPreferenceResponse> =>
    get<InterviewPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: InterviewPreferenceUpdateRequest): Promise<InterviewPreferenceResponse> =>
    put<InterviewPreferenceResponse>(`${BASE}/preferences`, data),

  getPrep: (prepId: string): Promise<InterviewPrepResponse> =>
    get<InterviewPrepResponse>(`${BASE}/${prepId}`),

  deletePrep: (prepId: string): Promise<void> =>
    del<void>(`${BASE}/${prepId}`),

  generateQuestions: (prepId: string, data: GenerateQuestionsRequest): Promise<InterviewQuestionResponse[]> =>
    post<InterviewQuestionResponse[]>(`${BASE}/${prepId}/questions`, data),

  generateStarExamples: (prepId: string, data: GenerateSTARExamplesRequest): Promise<STARExampleResponse[]> =>
    post<STARExampleResponse[]>(`${BASE}/${prepId}/star-examples`, data),

  generateNegotiationScript: (
    prepId: string,
    data: GenerateNegotiationScriptRequest,
  ): Promise<NegotiationScriptResponse> =>
    post<NegotiationScriptResponse>(`${BASE}/${prepId}/negotiation`, data),
};
