/**
 * PathForge — API Types: Cross-Engine Recommendation Intelligence™
 * ==================================================================
 * Types for recommendations, priority scoring, engine correlations, and batches.
 * Mirrors: apps/api/app/schemas/recommendation_intelligence.py
 */

// ── Priority Breakdown ────────────────────────────────────────

export interface PriorityBreakdown {
  readonly urgency: number;
  readonly impact: number;
  readonly inverse_effort: number;
  readonly final_score: number;
}

// ── Engine Correlation ────────────────────────────────────────

export interface EngineCorrelation {
  readonly engine_name: string;
  readonly display_name: string;
  readonly correlation_strength: number;
  readonly insight_summary: string;
}

// ── Correlation Response ──────────────────────────────────────

export interface RecommendationCorrelationResponse {
  readonly id: string;
  readonly recommendation_id: string;
  readonly engine_name: string;
  readonly correlation_strength: number;
  readonly insight_summary: string;
  readonly created_at: string;
}

// ── Recommendation ────────────────────────────────────────────

export interface CrossEngineRecommendationResponse {
  readonly id: string;
  readonly user_id: string;
  readonly batch_id: string | null;
  readonly recommendation_type: string;
  readonly status: string;
  readonly priority_score: number;
  readonly priority_breakdown: PriorityBreakdown | null;
  readonly effort_level: string;
  readonly expected_impact: string;
  readonly confidence_score: number;
  readonly title: string;
  readonly description: string;
  readonly action_items: string[] | null;
  readonly source_engines: string[] | null;
  readonly data_source: string;
  readonly disclaimer: string;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface RecommendationSummary {
  readonly id: string;
  readonly recommendation_type: string;
  readonly status: string;
  readonly priority_score: number;
  readonly effort_level: string;
  readonly title: string;
  readonly confidence_score: number;
  readonly created_at: string;
}

// ── Batch ─────────────────────────────────────────────────────

export interface RecommendationBatchResponse {
  readonly id: string;
  readonly user_id: string;
  readonly batch_type: string;
  readonly total_recommendations: number;
  readonly career_vitals_at_generation: number | null;
  readonly data_source: string;
  readonly created_at: string;
  readonly updated_at: string;
}

// ── Preferences ───────────────────────────────────────────────

export interface RecommendationPreferenceResponse {
  readonly id: string;
  readonly user_id: string;
  readonly enabled_categories: string[] | null;
  readonly min_priority_score: number;
  readonly max_recommendations_per_batch: number;
  readonly preferred_effort_levels: string[] | null;
  readonly notifications_enabled: boolean;
  readonly created_at: string;
  readonly updated_at: string;
}

// ── Dashboard ─────────────────────────────────────────────────

export interface RecommendationDashboardResponse {
  readonly latest_batch: RecommendationBatchResponse | null;
  readonly recent_recommendations: RecommendationSummary[];
  readonly total_pending: number;
  readonly total_completed: number;
  readonly preferences: RecommendationPreferenceResponse | null;
  readonly data_source: string;
  readonly disclaimer: string;
}

// ── Recommendation List ───────────────────────────────────────

export interface RecommendationListResponse {
  readonly items: CrossEngineRecommendationResponse[];
  readonly total: number;
  readonly limit: number;
  readonly offset: number;
}

// ── Request Schemas ───────────────────────────────────────────

export interface GenerateRecommendationsRequest {
  readonly batch_type?: string;
  readonly focus_categories?: string[] | null;
}

export interface UpdateRecommendationStatusRequest {
  readonly status: string;
  readonly notes?: string | null;
}

export interface RecommendationPreferenceUpdate {
  readonly enabled_categories?: string[] | null;
  readonly min_priority_score?: number | null;
  readonly max_recommendations_per_batch?: number | null;
  readonly preferred_effort_levels?: string[] | null;
  readonly notifications_enabled?: boolean | null;
}
