/**
 * PathForge — API Client: Cross-Engine Recommendation Intelligence™
 * ==================================================================
 * Recommendations, priority scoring, engine correlations, and batches.
 */

import { get, patch, post, put } from "@/lib/http";
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

const BASE = "/api/v1/recommendations";

export const recommendationApi = {
  getDashboard: (): Promise<RecommendationDashboardResponse> =>
    get<RecommendationDashboardResponse>(`${BASE}/dashboard`),

  generateRecommendations: (data: GenerateRecommendationsRequest): Promise<RecommendationBatchResponse> =>
    post<RecommendationBatchResponse>(`${BASE}/generate`, data),

  listRecommendations: (
    status?: string,
    sortBy?: string,
    limit: number = 20,
    offset: number = 0,
  ): Promise<RecommendationListResponse> => {
    const params = new URLSearchParams();
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    if (status) params.set("status", status);
    if (sortBy) params.set("sort_by", sortBy);
    return get<RecommendationListResponse>(`${BASE}?${params.toString()}`);
  },

  getRecommendationDetail: (recommendationId: string): Promise<CrossEngineRecommendationResponse> =>
    get<CrossEngineRecommendationResponse>(`${BASE}/${recommendationId}`),

  updateRecommendationStatus: (
    recommendationId: string,
    data: UpdateRecommendationStatusRequest,
  ): Promise<CrossEngineRecommendationResponse> =>
    patch<CrossEngineRecommendationResponse>(`${BASE}/${recommendationId}/status`, data),

  getCorrelations: (recommendationId: string): Promise<RecommendationCorrelationResponse[]> =>
    get<RecommendationCorrelationResponse[]>(`${BASE}/${recommendationId}/correlations`),

  listBatches: (limit: number = 10): Promise<RecommendationBatchResponse[]> =>
    get<RecommendationBatchResponse[]>(`${BASE}/batches?limit=${limit}`),

  getPreferences: (): Promise<RecommendationPreferenceResponse> =>
    get<RecommendationPreferenceResponse>(`${BASE}/preferences`),

  updatePreferences: (data: RecommendationPreferenceUpdate): Promise<RecommendationPreferenceResponse> =>
    put<RecommendationPreferenceResponse>(`${BASE}/preferences`, data),
};
