/**
 * PathForge — Sprint 28: Actions Page Integration Tests
 * =======================================================
 * Cross-feature coherence: intelligence flows into action.
 * Tests the Actions page logic that merges recommendations + workflows.
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
import { workflowApi } from "@/lib/api-client/workflow-automation";
import type {
  RecommendationDashboardResponse,
  WorkflowDashboardResponse,
} from "@/types/api";

describe("Actions — Cross-Feature Coherence", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = mockFetch();
  });

  // ── Intelligence → Action Flow ────────────────────────────

  describe("Intelligence-to-Action coherence", () => {
    it("should fetch both recommendations and workflows for unified Actions view", async () => {
      const mockRecDashboard: RecommendationDashboardResponse = {
        latest_batch: null,
        recent_recommendations: [
          {
            id: "rec-1",
            recommendation_type: "skill_enhancement",
            status: "pending",
            priority_score: 85,
            effort_level: "medium",
            title: "Upskill in TypeScript",
            confidence_score: 0.9,
            created_at: "2026-02-26T12:00:00Z",
          },
        ],
        total_pending: 3,
        total_completed: 7,
        preferences: null,
        data_source: "career_intelligence",
        disclaimer: "AI-generated",
      };

      const mockWfDashboard: WorkflowDashboardResponse = {
        active_workflows: [
          {
            id: "wf-1",
            name: "TypeScript Upskilling Pipeline",
            workflow_status: "active",
            trigger_type: "recommendation",
            total_steps: 5,
            completed_steps: 2,
            is_template: false,
            created_at: "2026-02-26T12:00:00Z",
          },
        ],
        available_templates: [],
        total_active: 1,
        total_completed: 3,
        total_draft: 0,
        preferences: null,
        data_source: "workflow_automation",
        disclaimer: "AI-managed workflows",
      };

      // First call: recommendations dashboard
      fetchMock.mockResolvedValueOnce(mockFetchResponse(mockRecDashboard));
      const recs = await recommendationApi.getDashboard();

      // Second call: workflow dashboard
      fetchMock.mockResolvedValueOnce(mockFetchResponse(mockWfDashboard));
      const workflows = await workflowApi.getDashboard();

      // Verify both data sources are available for unified rendering
      expect(recs.total_pending).toBe(3);
      expect(recs.recent_recommendations).toHaveLength(1);
      expect(workflows.active_workflows).toHaveLength(1);
      expect(workflows.total_active).toBe(1);

      // Verify workflow describes its trigger source
      expect(workflows.active_workflows[0].trigger_type).toBe("recommendation");
    });

    it("should maintain recommendation explainability in unified view", async () => {
      const mockRecDashboard: RecommendationDashboardResponse = {
        latest_batch: null,
        recent_recommendations: [
          {
            id: "rec-1",
            recommendation_type: "career_pivot",
            status: "pending",
            priority_score: 92,
            effort_level: "high",
            title: "Consider Architect Role Transition",
            confidence_score: 0.88,
            created_at: "2026-02-26T12:00:00Z",
          },
        ],
        total_pending: 1,
        total_completed: 0,
        preferences: null,
        data_source: "career_intelligence",
        disclaimer: "AI-generated",
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockRecDashboard));

      const result = await recommendationApi.getDashboard();

      // In the Actions page, each recommendation must carry:
      // - priority_score for sorting
      // - confidence_score for trust
      // - effort_level for user decision-making
      // - recommendation_type for categorization
      const rec = result.recent_recommendations[0];
      expect(rec.priority_score).toBeGreaterThan(0);
      expect(rec.confidence_score).toBeGreaterThan(0);
      expect(rec.effort_level).toBeTruthy();
      expect(rec.recommendation_type).toBeTruthy();
    });
  });

  // ── Workflow Inline Execution ─────────────────────────────

  describe("Workflow inline execution", () => {
    it("should support step-level status updates without page navigation", async () => {
      const mockWorkflow = {
        id: "wf-1",
        user_id: "user-1",
        name: "Reskilling Pipeline",
        description: "Close skill gap in Cloud Architecture",
        workflow_status: "active",
        trigger_type: "recommendation",
        trigger_config: null,
        total_steps: 4,
        completed_steps: 2,
        is_template: false,
        template_category: null,
        source_engine: "skill-decay",
        source_recommendation_id: "rec-1",
        data_source: "workflow_automation",
        disclaimer: "AI-managed",
        created_at: "2026-02-26T12:00:00Z",
        updated_at: "2026-02-26T12:00:00Z",
      };
      fetchMock.mockResolvedValue(mockFetchResponse(mockWorkflow));

      const result = await workflowApi.updateStepStatus("wf-1", "step-3", {
        action: "complete",
        notes: "Finished online course",
      });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/wf-1/steps/step-3"),
        expect.objectContaining({ method: "PATCH" }),
      );
      expect(result.source_recommendation_id).toBe("rec-1");
    });
  });
});
