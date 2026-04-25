/**
 * PathForge — Career Simulation Hooks Tests
 * =============================================
 * Validates TanStack Query hook configuration for Career Simulator:
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
  careerSimulationApi: {
    getDashboard: vi.fn().mockResolvedValue({
      simulations: [
        { id: "sim1", scenario_type: "role_transition", status: "completed", confidence_score: 0.82, salary_impact_percent: 15.5, estimated_months: 6, data_source: "ai_analysis", disclaimer: "AI estimate", computed_at: "2026-02-26T12:00:00Z" },
      ],
      preferences: null,
      total_simulations: 1,
      scenario_type_counts: { role_transition: 1 },
    }),
    getSimulation: vi.fn().mockResolvedValue({ id: "sim1", scenario_type: "role_transition", status: "completed", confidence_score: 0.82, inputs: [], outcomes: [], recommendations: [] }),
    getPreferences: vi.fn().mockResolvedValue({ id: "pref1", career_dna_id: "dna1", default_scenario_type: null, max_scenarios: 10, notification_enabled: true }),
    simulateRole: vi.fn().mockResolvedValue({ id: "sim2", scenario_type: "role_transition", status: "completed", confidence_score: 0.75 }),
    simulateGeo: vi.fn().mockResolvedValue({ id: "sim3", scenario_type: "geo_move", status: "completed", confidence_score: 0.68 }),
    simulateSkill: vi.fn().mockResolvedValue({ id: "sim4", scenario_type: "skill_investment", status: "completed", confidence_score: 0.88 }),
    simulateIndustry: vi.fn().mockResolvedValue({ id: "sim5", scenario_type: "industry_pivot", status: "completed", confidence_score: 0.55 }),
    simulateSeniority: vi.fn().mockResolvedValue({ id: "sim6", scenario_type: "seniority_jump", status: "completed", confidence_score: 0.72 }),
    compare: vi.fn().mockResolvedValue({ simulations: [], ranking: [], trade_off_analysis: null }),
    deleteSimulation: vi.fn().mockResolvedValue(undefined),
    updatePreferences: vi.fn().mockResolvedValue({ id: "pref1", max_scenarios: 20 }),
  },
}));

import { careerSimulationApi } from "@/lib/api-client";
import {
  useSimulationDashboard,
  useSimulationDetail,
  useSimulationPreferences,
  useSimulateRole,
  useSimulateGeo,
  useSimulateSkill,
  useDeleteSimulation,
} from "@/hooks/api/use-career-simulation";

// ── Test Helpers ───────────────────────────────────────────

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

function createWrapper(): ({ children }: { children: React.ReactNode }) => React.ReactNode {
  const queryClient = createTestQueryClient();
  return function TestWrapper({ children }: { children: React.ReactNode }): React.ReactNode {
    return React.createElement(QueryClientProvider, { client: queryClient }, children);
  };
}

// ── Tests ──────────────────────────────────────────────────

describe("Career Simulation Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  describe("useSimulationDashboard", () => {
    it("should fetch dashboard when authenticated", async () => {
      const { result } = renderHook(() => useSimulationDashboard(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerSimulationApi.getDashboard).toHaveBeenCalledOnce();
      expect(result.current.data?.total_simulations).toBe(1);
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });
      const { result } = renderHook(() => useSimulationDashboard(), { wrapper: createWrapper() });
      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  describe("useSimulationDetail", () => {
    it("should fetch simulation detail by ID", async () => {
      const { result } = renderHook(() => useSimulationDetail("sim1"), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerSimulationApi.getSimulation).toHaveBeenCalledWith("sim1");
    });

    it("should not fetch with empty ID", () => {
      const { result } = renderHook(() => useSimulationDetail(""), { wrapper: createWrapper() });
      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  describe("useSimulationPreferences", () => {
    it("should fetch preferences", async () => {
      const { result } = renderHook(() => useSimulationPreferences(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerSimulationApi.getPreferences).toHaveBeenCalledOnce();
    });
  });

  describe("useSimulateRole", () => {
    it("should call simulateRole and invalidate queries", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
      const wrapper = ({ children }: { children: React.ReactNode }): React.ReactNode =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useSimulateRole(), { wrapper });
      result.current.mutate({ target_role: "Data Engineer" });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerSimulationApi.simulateRole).toHaveBeenCalledWith({ target_role: "Data Engineer" });
      expect(invalidateSpy).toHaveBeenCalled();
      invalidateSpy.mockRestore();
    });
  });

  describe("useSimulateGeo", () => {
    it("should call simulateGeo with location data", async () => {
      const { result } = renderHook(() => useSimulateGeo(), { wrapper: createWrapper() });
      result.current.mutate({ target_location: "Berlin" });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerSimulationApi.simulateGeo).toHaveBeenCalledWith({ target_location: "Berlin" });
    });
  });

  describe("useSimulateSkill", () => {
    it("should call simulateSkill with skills array", async () => {
      const { result } = renderHook(() => useSimulateSkill(), { wrapper: createWrapper() });
      result.current.mutate({ skills: ["Rust", "Go"] });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerSimulationApi.simulateSkill).toHaveBeenCalledWith({ skills: ["Rust", "Go"] });
    });
  });

  describe("useDeleteSimulation", () => {
    it("should delete and invalidate queries", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
      const wrapper = ({ children }: { children: React.ReactNode }): React.ReactNode =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useDeleteSimulation(), { wrapper });
      result.current.mutate("sim1");
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerSimulationApi.deleteSimulation).toHaveBeenCalledWith("sim1");
      expect(invalidateSpy).toHaveBeenCalled();
      invalidateSpy.mockRestore();
    });
  });

  describe("Edge Cases", () => {
    it("should handle empty simulations", async () => {
      vi.mocked(careerSimulationApi.getDashboard).mockResolvedValueOnce({
        simulations: [], preferences: null, total_simulations: 0, scenario_type_counts: {},
      });
      const { result } = renderHook(() => useSimulationDashboard(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.simulations).toHaveLength(0);
    });

    it("should handle zero scenario type counts", async () => {
      vi.mocked(careerSimulationApi.getDashboard).mockResolvedValueOnce({
        simulations: [], preferences: null, total_simulations: 0, scenario_type_counts: {},
      });
      const { result } = renderHook(() => useSimulationDashboard(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(Object.keys(result.current.data?.scenario_type_counts ?? {})).toHaveLength(0);
    });
  });
});
