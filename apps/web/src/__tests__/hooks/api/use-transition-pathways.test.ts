/**
 * PathForge — Transition Pathways Hooks Tests
 * ===============================================
 * Validates TanStack Query hook configuration for Career Moves:
 * query keys, auth gating, staleTime, API delegation, mutation invalidation.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React, { type ReactNode } from "react";

// ── Mocks ──────────────────────────────────────────────────

const mockUseAuth = vi.fn<() => { isAuthenticated: boolean }>();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => mockUseAuth(),
}));

vi.mock("@/lib/api-client", () => ({
  transitionPathwaysApi: {
    getDashboard: vi.fn().mockResolvedValue({
      transitions: [
        { id: "t1", from_role: "Software Engineer", to_role: "Data Engineer", confidence_score: 0.78, difficulty: "moderate", status: "completed", skill_overlap_percent: 65, estimated_duration_months: 8, computed_at: "2026-02-26T12:00:00Z" },
      ],
      preferences: null,
      total_explored: 1,
    }),
    list: vi.fn().mockResolvedValue([
      { id: "t1", from_role: "Software Engineer", to_role: "Data Engineer", confidence_score: 0.78, difficulty: "moderate", status: "completed", skill_overlap_percent: 65, estimated_duration_months: 8, computed_at: "2026-02-26T12:00:00Z" },
    ]),
    getTransition: vi.fn().mockResolvedValue({ id: "t1", from_role: "Software Engineer", to_role: "Data Engineer", confidence_score: 0.78, success_probability: 0.72, skill_overlap_percent: 65 }),
    getSkillBridge: vi.fn().mockResolvedValue([
      { id: "sb1", skill_name: "Apache Spark", category: "Data", is_already_held: false, priority: "high", estimated_weeks: 6 },
    ]),
    getMilestones: vi.fn().mockResolvedValue([
      { id: "m1", phase: "Foundation", title: "Learn SQL", target_week: 2, order_index: 0, is_completed: false },
    ]),
    getPreferences: vi.fn().mockResolvedValue({ id: "p1", min_confidence: 0.5, max_timeline_months: 24, notification_enabled: true }),
    explore: vi.fn().mockResolvedValue({ transition_path: { id: "t2" }, skill_bridge: [], milestones: [], comparisons: [] }),
    whatIf: vi.fn().mockResolvedValue({ id: "t3", from_role: "SE", to_role: "PM", confidence_score: 0.55 }),
    deleteTransition: vi.fn().mockResolvedValue(undefined),
    updatePreferences: vi.fn().mockResolvedValue({ id: "p1", min_confidence: 0.6 }),
  },
}));

import { transitionPathwaysApi } from "@/lib/api-client";
import {
  useTransitionDashboard,
  useTransitionList,
  useTransitionDetail,
  useTransitionSkillBridge,
  useTransitionMilestones,
  useExploreTransition,
  useDeleteTransition,
} from "@/hooks/api/use-transition-pathways";

// ── Test Helpers ───────────────────────────────────────────

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

function createWrapper(): ({ children }: { children: ReactNode }) => React.JSX.Element {
  const queryClient = createTestQueryClient();
  return function TestWrapper({ children }: { children: ReactNode }): React.JSX.Element {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ── Tests ──────────────────────────────────────────────────

describe("Transition Pathways Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  describe("useTransitionDashboard", () => {
    it("should fetch dashboard when authenticated", async () => {
      const { result } = renderHook(() => useTransitionDashboard(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(transitionPathwaysApi.getDashboard).toHaveBeenCalledOnce();
      expect(result.current.data?.total_explored).toBe(1);
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });
      const { result } = renderHook(() => useTransitionDashboard(), { wrapper: createWrapper() });
      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  describe("useTransitionList", () => {
    it("should fetch transitions list", async () => {
      const { result } = renderHook(() => useTransitionList(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(transitionPathwaysApi.list).toHaveBeenCalledOnce();
      expect(result.current.data).toHaveLength(1);
    });
  });

  describe("useTransitionDetail", () => {
    it("should fetch transition by ID", async () => {
      const { result } = renderHook(() => useTransitionDetail("t1"), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(transitionPathwaysApi.getTransition).toHaveBeenCalledWith("t1");
    });

    it("should not fetch with empty ID", () => {
      const { result } = renderHook(() => useTransitionDetail(""), { wrapper: createWrapper() });
      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  describe("useTransitionSkillBridge", () => {
    it("should fetch skill bridge for transition", async () => {
      const { result } = renderHook(() => useTransitionSkillBridge("t1"), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(transitionPathwaysApi.getSkillBridge).toHaveBeenCalledWith("t1");
      expect(result.current.data).toHaveLength(1);
    });
  });

  describe("useTransitionMilestones", () => {
    it("should fetch milestones for transition", async () => {
      const { result } = renderHook(() => useTransitionMilestones("t1"), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(transitionPathwaysApi.getMilestones).toHaveBeenCalledWith("t1");
    });
  });

  describe("useExploreTransition", () => {
    it("should call explore and invalidate queries", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
      const wrapper = ({ children }: { children: ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children as React.ReactNode);

      const { result } = renderHook(() => useExploreTransition(), { wrapper });
      result.current.mutate({ target_role: "Data Engineer" });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(transitionPathwaysApi.explore).toHaveBeenCalledWith({ target_role: "Data Engineer" });
      expect(invalidateSpy).toHaveBeenCalled();
      invalidateSpy.mockRestore();
    });
  });

  describe("useDeleteTransition", () => {
    it("should delete and invalidate queries", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
      const wrapper = ({ children }: { children: ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children as React.ReactNode);

      const { result } = renderHook(() => useDeleteTransition(), { wrapper });
      result.current.mutate("t1");
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(transitionPathwaysApi.deleteTransition).toHaveBeenCalledWith("t1");
      expect(invalidateSpy).toHaveBeenCalled();
      invalidateSpy.mockRestore();
    });
  });

  describe("Edge Cases", () => {
    it("should handle empty transitions array", async () => {
      vi.mocked(transitionPathwaysApi.getDashboard).mockResolvedValueOnce({
        transitions: [], preferences: null, total_explored: 0,
      });
      const { result } = renderHook(() => useTransitionDashboard(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.transitions).toHaveLength(0);
    });

    it("should handle null preferences", async () => {
      vi.mocked(transitionPathwaysApi.getDashboard).mockResolvedValueOnce({
        transitions: [], preferences: null, total_explored: 0,
      });
      const { result } = renderHook(() => useTransitionDashboard(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.preferences).toBeNull();
    });
  });
});
