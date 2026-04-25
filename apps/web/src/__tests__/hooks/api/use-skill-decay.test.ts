/**
 * PathForge — Skill Decay Hooks Tests
 * ======================================
 * Validates TanStack Query hook configuration for Skills Health:
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
  skillDecayApi: {
    getDashboard: vi.fn().mockResolvedValue({
      freshness: [
        { id: "f1", skill_name: "Python", freshness_score: 72, category: "Programming", half_life_days: 180, decay_rate: "moderate", days_since_active: 45, refresh_urgency: 0.4, analysis_reasoning: null, computed_at: "2026-02-26T12:00:00Z", last_active_date: "2026-01-12T00:00:00Z" },
      ],
      freshness_summary: { average: 72 },
      market_demand: [],
      velocity: [],
      reskilling_pathways: [],
      preference: null,
      last_scan_at: "2026-02-26T12:00:00Z",
    }),
    getFreshness: vi.fn().mockResolvedValue([
      { id: "f1", skill_name: "Python", freshness_score: 72, category: "Programming", half_life_days: 180, decay_rate: "moderate", days_since_active: 45, refresh_urgency: 0.4, analysis_reasoning: null, computed_at: "2026-02-26T12:00:00Z", last_active_date: "2026-01-12T00:00:00Z" },
    ]),
    getVelocityMap: vi.fn().mockResolvedValue([]),
    getReskillingPathways: vi.fn().mockResolvedValue([]),
    getPreferences: vi.fn().mockResolvedValue({
      id: "pref-1", tracking_enabled: true, notification_frequency: "weekly", decay_alert_threshold: 40, focus_categories: null, excluded_skills: null,
    }),
    triggerScan: vi.fn().mockResolvedValue({
      status: "completed", skills_analyzed: 5, freshness: [], market_demand: [], velocity: [], reskilling_pathways: [],
    }),
    refreshSkill: vi.fn().mockResolvedValue({
      id: "f2", skill_name: "Python", freshness_score: 95, category: "Programming", half_life_days: 180, decay_rate: "low", days_since_active: 0, refresh_urgency: 0.1, analysis_reasoning: null, computed_at: "2026-02-26T12:00:00Z", last_active_date: "2026-02-26T00:00:00Z",
    }),
    updatePreferences: vi.fn().mockResolvedValue({
      id: "pref-1", tracking_enabled: false, notification_frequency: "weekly", decay_alert_threshold: 40, focus_categories: null, excluded_skills: null,
    }),
  },
}));

import { skillDecayApi } from "@/lib/api-client";
import {
  useSkillDecayDashboard,
  useSkillFreshness,
  useSkillVelocityMap,
  useReskillingPathways,
  useSkillDecayPreferences,
  useTriggerDecayScan,
  useRefreshSkill,
  useUpdateSkillDecayPreferences,
} from "@/hooks/api/use-skill-decay";

// ── Test Helpers ───────────────────────────────────────────

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

function createWrapper(): ({ children }: { children: ReactNode }) => React.ReactNode {
  const queryClient = createTestQueryClient();
  return function TestWrapper({ children }: { children: ReactNode }): React.ReactNode {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ── Tests ──────────────────────────────────────────────────

describe("Skill Decay Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  // ── useSkillDecayDashboard ──────────────────────────────

  describe("useSkillDecayDashboard", () => {
    it("should fetch dashboard when authenticated", async () => {
      const { result } = renderHook(() => useSkillDecayDashboard(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(skillDecayApi.getDashboard).toHaveBeenCalledOnce();
      expect(result.current.data?.freshness).toHaveLength(1);
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });

      const { result } = renderHook(() => useSkillDecayDashboard(), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(skillDecayApi.getDashboard).not.toHaveBeenCalled();
    });
  });

  // ── useSkillFreshness ───────────────────────────────────

  describe("useSkillFreshness", () => {
    it("should fetch freshness data with correct API method", async () => {
      const { result } = renderHook(() => useSkillFreshness(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(skillDecayApi.getFreshness).toHaveBeenCalledOnce();
      expect(result.current.data?.[0]?.skill_name).toBe("Python");
    });
  });

  // ── useSkillVelocityMap ─────────────────────────────────

  describe("useSkillVelocityMap", () => {
    it("should fetch velocity map data", async () => {
      const { result } = renderHook(() => useSkillVelocityMap(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(skillDecayApi.getVelocityMap).toHaveBeenCalledOnce();
    });
  });

  // ── useReskillingPathways ───────────────────────────────

  describe("useReskillingPathways", () => {
    it("should fetch reskilling pathways", async () => {
      const { result } = renderHook(() => useReskillingPathways(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(skillDecayApi.getReskillingPathways).toHaveBeenCalledOnce();
    });
  });

  // ── useSkillDecayPreferences ────────────────────────────

  describe("useSkillDecayPreferences", () => {
    it("should fetch preferences when authenticated", async () => {
      const { result } = renderHook(() => useSkillDecayPreferences(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(skillDecayApi.getPreferences).toHaveBeenCalledOnce();
      expect(result.current.data?.tracking_enabled).toBe(true);
    });
  });

  // ── useTriggerDecayScan ─────────────────────────────────

  describe("useTriggerDecayScan", () => {
    it("should call triggerScan API method", async () => {
      const { result } = renderHook(() => useTriggerDecayScan(), {
        wrapper: createWrapper(),
      });

      result.current.mutate();

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(skillDecayApi.triggerScan).toHaveBeenCalledOnce();
    });

    it("should invalidate all skill-decay queries on success", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: ReactNode }): React.ReactNode =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useTriggerDecayScan(), { wrapper });

      result.current.mutate();

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: expect.arrayContaining(["skill-decay"]) }),
      );

      invalidateSpy.mockRestore();
    });
  });

  // ── useRefreshSkill ─────────────────────────────────────

  describe("useRefreshSkill", () => {
    it("should call refreshSkill with skill data", async () => {
      const { result } = renderHook(() => useRefreshSkill(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ skill_name: "Python" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(skillDecayApi.refreshSkill).toHaveBeenCalledWith({ skill_name: "Python" });
    });
  });

  // ── useUpdateSkillDecayPreferences ──────────────────────

  describe("useUpdateSkillDecayPreferences", () => {
    it("should call updatePreferences and invalidate preferences query", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: ReactNode }): React.ReactNode =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useUpdateSkillDecayPreferences(), { wrapper });

      result.current.mutate({ tracking_enabled: false });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(skillDecayApi.updatePreferences).toHaveBeenCalledWith({ tracking_enabled: false });

      expect(invalidateSpy).toHaveBeenCalled();
      invalidateSpy.mockRestore();
    });
  });

  // ── Edge Cases ──────────────────────────────────────────

  describe("Edge Cases", () => {
    it("should handle empty freshness array", async () => {
      vi.mocked(skillDecayApi.getDashboard).mockResolvedValueOnce({
        freshness: [], freshness_summary: {}, market_demand: [], velocity: [], reskilling_pathways: [], preference: null, last_scan_at: null,
      });

      const { result } = renderHook(() => useSkillDecayDashboard(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.freshness).toHaveLength(0);
      expect(result.current.data?.last_scan_at).toBeNull();
    });

    it("should handle null preference response", async () => {
      vi.mocked(skillDecayApi.getDashboard).mockResolvedValueOnce({
        freshness: [], freshness_summary: {}, market_demand: [], velocity: [], reskilling_pathways: [], preference: null, last_scan_at: null,
      });

      const { result } = renderHook(() => useSkillDecayDashboard(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.preference).toBeNull();
    });
  });
});
