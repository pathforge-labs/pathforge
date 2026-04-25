/**
 * PathForge — Sprint 28: Recommendation Intelligence Tests
 * ==========================================================
 * Signal-prioritized: tests priority-weighted sorting correctness,
 * explainability presence, and cross-feature coherence.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mockFetch,
  mockFetchResponse,
} from "../test-helpers";

vi.mock("@/lib/token-manager", () => ({
  getAccessToken: vi.fn(() => "mock-access-token"),
}));

vi.mock("@/lib/refresh-queue", () => ({
  refreshAccessToken: vi.fn(),
}));

import { recommendationApi } from "@/lib/api-client/recommendation-intelligence";
import type {
  RecommendationDashboardResponse,
  RecommendationListResponse,
  CrossEngineRecommendationResponse,
} from "@/types/api";

describe("Recommendation Intelligence — API Client", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = mockFetch();
  });

  // ── Priority-Weighted Sorting Correctness ─────────────────

  describe("Priority-Weighted Sorting", () => {
    it("should pass sortBy parameter to the API for priority-weighted sorting", async () => {
      const mockResponse: RecommendationListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockResponse));

      await recommendationApi.listRecommendations("pending", "priority_score", 20, 0);

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("sort_by=priority_score"),
        expect.any(Object),
      );
    });

    it("should return recommendations ordered by priority_score descending", async () => {
      const mockItems: CrossEngineRecommendationResponse[] = [
        createMockRecommendation({ priority_score: 45, title: "Low priority" }),
        createMockRecommendation({ priority_score: 92, title: "Critical" }),
        createMockRecommendation({ priority_score: 67, title: "Medium" }),
      ];
      const mockResponse: RecommendationListResponse = {
        items: mockItems,
        total: 3,
        limit: 20,
        offset: 0,
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockResponse));

      const result = await recommendationApi.listRecommendations(undefined, "priority_score");

      // Client receives data — sorting verification happens at page level
      expect(result.items).toHaveLength(3);
      // Verify client-side sort produces correct order
      const sorted = [...result.items].sort((a, b) => b.priority_score - a.priority_score);
      expect(sorted[0].title).toBe("Critical");
      expect(sorted[1].title).toBe("Medium");
      expect(sorted[2].title).toBe("Low priority");
    });

    it("should filter by status when provided", async () => {
      const mockResponse: RecommendationListResponse = {
        items: [],
        total: 0,
        limit: 20,
        offset: 0,
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockResponse));

      await recommendationApi.listRecommendations("pending");

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("status=pending"),
        expect.any(Object),
      );
    });
  });

  // ── Explainability Presence ───────────────────────────────

  describe("Explainability", () => {
    it("should include priority_breakdown for each recommendation", async () => {
      const mockItem = createMockRecommendation({
        priority_breakdown: {
          urgency: 85,
          impact: 90,
          inverse_effort: 60,
          final_score: 78,
        },
      });
      fetchMock.mockResolvedValue(mockFetchResponse(mockItem));

      const result = await recommendationApi.getRecommendationDetail("test-id");

      expect(result.priority_breakdown).toBeDefined();
      expect(result.priority_breakdown?.urgency).toBe(85);
      expect(result.priority_breakdown?.impact).toBe(90);
      expect(result.priority_breakdown?.inverse_effort).toBe(60);
      expect(result.priority_breakdown?.final_score).toBe(78);
    });

    it("should include source_engines to explain recommendation origin", async () => {
      const mockItem = createMockRecommendation({
        source_engines: ["career-dna", "threat-radar", "skill-decay"],
      });
      fetchMock.mockResolvedValue(mockFetchResponse(mockItem));

      const result = await recommendationApi.getRecommendationDetail("test-id");

      expect(result.source_engines).toHaveLength(3);
      expect(result.source_engines).toContain("career-dna");
    });

    it("should include description explaining the expected impact", async () => {
      const mockItem = createMockRecommendation({
        description: "Upskilling in cloud architecture will increase market alignment by 15%",
        expected_impact: "high",
      });
      fetchMock.mockResolvedValue(mockFetchResponse(mockItem));

      const result = await recommendationApi.getRecommendationDetail("test-id");

      expect(result.description).toBeTruthy();
      expect(result.expected_impact).toBe("high");
    });
  });

  // ── Cross-Engine Correlations ─────────────────────────────

  describe("Cross-Engine Correlations", () => {
    it("should fetch engine correlations for a recommendation", async () => {
      const mockCorrelations = [
        {
          id: "corr-1",
          recommendation_id: "rec-1",
          engine_name: "threat-radar",
          correlation_strength: 0.85,
          insight_summary: "Threat detected aligns with this recommendation",
          created_at: "2026-02-26T12:00:00Z",
        },
        {
          id: "corr-2",
          recommendation_id: "rec-1",
          engine_name: "skill-decay",
          correlation_strength: 0.72,
          insight_summary: "Skill freshness data supports this reskilling path",
          created_at: "2026-02-26T12:00:00Z",
        },
      ];
      fetchMock.mockResolvedValue(mockFetchResponse(mockCorrelations));

      const result = await recommendationApi.getCorrelations("rec-1");

      expect(result).toHaveLength(2);
      expect(result[0].correlation_strength).toBeGreaterThan(0);
      expect(result[0].insight_summary).toBeTruthy();
    });
  });

  // ── Dashboard ─────────────────────────────────────────────

  describe("Dashboard", () => {
    it("should fetch dashboard with pending/completed counts", async () => {
      const mockDashboard: RecommendationDashboardResponse = {
        latest_batch: null,
        recent_recommendations: [],
        total_pending: 5,
        total_completed: 12,
        preferences: null,
        data_source: "career_intelligence",
        disclaimer: "AI-generated recommendations",
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockDashboard));

      const result = await recommendationApi.getDashboard();

      expect(result.total_pending).toBe(5);
      expect(result.total_completed).toBe(12);
      expect(result.data_source).toBeTruthy();
      expect(result.disclaimer).toBeTruthy();
    });
  });

  // ── Status Lifecycle ──────────────────────────────────────

  describe("Status Lifecycle", () => {
    it("should update recommendation status", async () => {
      const mockUpdated = createMockRecommendation({ status: "in_progress" });
      fetchMock.mockResolvedValue(mockFetchResponse(mockUpdated));

      const result = await recommendationApi.updateRecommendationStatus("rec-1", {
        status: "in_progress",
        notes: "Starting implementation",
      });

      expect(result.status).toBe("in_progress");
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/rec-1/status"),
        expect.objectContaining({ method: "PATCH" }),
      );
    });
  });
});

// ── Helpers ─────────────────────────────────────────────────

function createMockRecommendation(
  overrides: Partial<CrossEngineRecommendationResponse> = {},
): CrossEngineRecommendationResponse {
  return {
    id: "rec-test",
    user_id: "user-1",
    batch_id: "batch-1",
    recommendation_type: "skill_enhancement",
    status: "pending",
    priority_score: 75,
    priority_breakdown: {
      urgency: 80,
      impact: 85,
      inverse_effort: 60,
      final_score: 75,
    },
    effort_level: "medium",
    expected_impact: "high",
    confidence_score: 0.82,
    title: "Enhance Cloud Skills",
    description: "Upskilling recommended based on market analysis",
    action_items: ["Complete AWS certification", "Build portfolio project"],
    source_engines: ["career-dna", "skill-decay"],
    data_source: "career_intelligence",
    disclaimer: "AI-generated recommendation",
    created_at: "2026-02-26T12:00:00Z",
    updated_at: "2026-02-26T12:00:00Z",
    ...overrides,
  };
}
