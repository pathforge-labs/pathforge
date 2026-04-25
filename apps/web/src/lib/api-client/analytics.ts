/**
 * PathForge — Analytics API Client
 * ==================================
 * Domain-split API client for analytics pipeline endpoints.
 * Replaces the `analytics` namespace from the legacy `lib/api.ts` monolith.
 */

import { fetchWithAuth } from "@/lib/http";
import type {
  FunnelStage,
  FunnelEventResponse,
  FunnelMetricsResponse,
  FunnelTimelineResponse,
  MarketInsightsListResponse,
  MarketInsightResponse,
  InsightType,
  CVExperimentsListResponse,
  CVExperimentResponse,
} from "@/types/api/analytics";

// ── Funnel Pipeline ────────────────────────────────────────

/** Record a funnel stage event. */
export function recordFunnelEvent(
  stage: FunnelStage,
  applicationId?: string,
  metadata?: Record<string, unknown>,
): Promise<FunnelEventResponse> {
  return fetchWithAuth<FunnelEventResponse>("/api/v1/analytics/funnel/events", {
    method: "POST",
    body: JSON.stringify({
      stage,
      application_id: applicationId,
      metadata,
    }),
  });
}

/** Get funnel metrics for a given period. */
export function getFunnelMetrics(
  period: string = "30d",
): Promise<FunnelMetricsResponse> {
  return fetchWithAuth<FunnelMetricsResponse>(
    `/api/v1/analytics/funnel/metrics?period=${period}`,
  );
}

/** Get funnel timeline data. */
export function getFunnelTimeline(
  days: number = 30,
): Promise<FunnelTimelineResponse> {
  return fetchWithAuth<FunnelTimelineResponse>(
    `/api/v1/analytics/funnel/timeline?days=${days}`,
  );
}

// ── Market Intelligence ────────────────────────────────────

/** Get all market insights. */
export function getMarketInsights(): Promise<MarketInsightsListResponse> {
  return fetchWithAuth<MarketInsightsListResponse>(
    "/api/v1/analytics/market/insights",
  );
}

/** Generate a new market insight. */
export function generateInsight(
  insightType: InsightType,
  period: string = "30d",
): Promise<MarketInsightResponse> {
  return fetchWithAuth<MarketInsightResponse>(
    "/api/v1/analytics/market/insights/generate",
    {
      method: "POST",
      body: JSON.stringify({ insight_type: insightType, period }),
    },
  );
}

// ── CV Experiments ─────────────────────────────────────────

/** List all CV A/B experiments. */
export function listExperiments(): Promise<CVExperimentsListResponse> {
  return fetchWithAuth<CVExperimentsListResponse>(
    "/api/v1/analytics/experiments",
  );
}

/** Create a new CV A/B experiment. */
export function createExperiment(
  jobListingId: string,
  variantAId: string,
  variantBId: string,
  hypothesis?: string,
): Promise<CVExperimentResponse> {
  return fetchWithAuth<CVExperimentResponse>("/api/v1/analytics/experiments", {
    method: "POST",
    body: JSON.stringify({
      job_listing_id: jobListingId,
      variant_a_id: variantAId,
      variant_b_id: variantBId,
      hypothesis,
    }),
  });
}

/** Record the result of a CV experiment. */
export function recordResult(
  experimentId: string,
  winnerId: string,
  metrics?: Record<string, unknown>,
): Promise<CVExperimentResponse> {
  return fetchWithAuth<CVExperimentResponse>(
    `/api/v1/analytics/experiments/${experimentId}/result`,
    {
      method: "PATCH",
      body: JSON.stringify({ winner_id: winnerId, metrics }),
    },
  );
}
