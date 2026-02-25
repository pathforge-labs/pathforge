/**
 * PathForge — Analytics Types
 * =============================
 * TypeScript interfaces for analytics pipeline endpoints.
 */

// ── Funnel Pipeline ────────────────────────────────────────

export type FunnelStage =
  | "viewed"
  | "saved"
  | "cv_tailored"
  | "applied"
  | "interviewing"
  | "offered"
  | "accepted"
  | "rejected"
  | "withdrawn";

export interface FunnelEventResponse {
  id: string;
  user_id: string;
  application_id: string | null;
  stage: FunnelStage;
  metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface FunnelStageMetric {
  stage: FunnelStage;
  count: number;
  conversion_rate: number;
}

export interface FunnelMetricsResponse {
  user_id: string;
  period: string;
  total_events: number;
  stages: FunnelStageMetric[];
}

export interface FunnelTimelinePoint {
  date: string;
  stage: FunnelStage;
  count: number;
}

export interface FunnelTimelineResponse {
  user_id: string;
  days: number;
  data: FunnelTimelinePoint[];
}

// ── Market Intelligence ────────────────────────────────────

export type InsightType =
  | "skill_demand"
  | "salary_trend"
  | "market_heat"
  | "competition_level"
  | "application_velocity";

export interface MarketInsightResponse {
  id: string;
  user_id: string;
  insight_type: InsightType;
  data: Record<string, unknown>;
  period: string;
  generated_at: string;
}

export interface MarketInsightsListResponse {
  user_id: string;
  insights: MarketInsightResponse[];
  count: number;
}

// ── CV Experiments ─────────────────────────────────────────

export type ExperimentStatus = "running" | "completed" | "cancelled";

export interface CVExperimentResponse {
  id: string;
  user_id: string;
  job_listing_id: string;
  variant_a_id: string;
  variant_b_id: string;
  winner_id: string | null;
  status: ExperimentStatus;
  metrics: Record<string, unknown> | null;
  hypothesis: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface CVExperimentsListResponse {
  user_id: string;
  experiments: CVExperimentResponse[];
  count: number;
}
