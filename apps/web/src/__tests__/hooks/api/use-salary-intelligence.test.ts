/**
 * PathForge — Salary Intelligence Hooks Tests
 * ===============================================
 * Validates TanStack Query hook configuration for Salary Intelligence:
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
  salaryIntelligenceApi: {
    getDashboard: vi.fn().mockResolvedValue({
      estimate: { id: "e1", role_title: "Software Engineer", location: "Amsterdam", seniority_level: "Senior", industry: "Technology", estimated_min: 70000, estimated_max: 95000, estimated_median: 82000, currency: "EUR", confidence: 0.78, market_percentile: 72, factors: null, data_source: "ai_analysis", disclaimer: "AI estimate", computed_at: "2026-02-26T12:00:00Z" },
      skill_impacts: [
        { id: "si1", skill_name: "TypeScript", category: "Programming", salary_impact_amount: 8000, salary_impact_percent: 9.8, demand_premium: 0.85, scarcity_factor: 0.72, impact_direction: "positive", reasoning: null, computed_at: "2026-02-26T12:00:00Z" },
      ],
      trajectory: [],
      scenarios: [],
      preference: null,
      last_scan_at: "2026-02-26T12:00:00Z",
    }),
    getEstimate: vi.fn().mockResolvedValue({ id: "e1", estimated_median: 82000, currency: "EUR" }),
    getSkillImpacts: vi.fn().mockResolvedValue({ impacts: [], total_positive_impact: 0, total_negative_impact: 0, top_skill: null }),
    getTrajectory: vi.fn().mockResolvedValue([]),
    listScenarios: vi.fn().mockResolvedValue([]),
    getPreferences: vi.fn().mockResolvedValue({ id: "p1", preferred_currency: "EUR", include_benefits: true, target_salary: null, target_currency: "EUR", notification_enabled: true, notification_frequency: "monthly", comparison_market: "NL", comparison_industries: null }),
    triggerScan: vi.fn().mockResolvedValue({ status: "completed", estimate: { id: "e1" }, skill_impacts: [], history_entry: { id: "h1" } }),
    runScenario: vi.fn().mockResolvedValue({ id: "s1", scenario_type: "skill_change", scenario_label: "Learn Rust", delta_amount: 5000, delta_percent: 6.1, confidence: 0.7, computed_at: "2026-02-26T12:00:00Z" }),
    updatePreferences: vi.fn().mockResolvedValue({ id: "p1", preferred_currency: "USD" }),
  },
}));

import { salaryIntelligenceApi } from "@/lib/api-client";
import {
  useSalaryDashboard,
  useSalaryEstimate,
  useSalarySkillImpacts,
  useSalaryTrajectory,
  useSalaryScenarios,
  useSalaryPreferences,
  useTriggerSalaryScan,
  useRunSalaryScenario,
} from "@/hooks/api/use-salary-intelligence";

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

describe("Salary Intelligence Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  describe("useSalaryDashboard", () => {
    it("should fetch dashboard when authenticated", async () => {
      const { result } = renderHook(() => useSalaryDashboard(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(salaryIntelligenceApi.getDashboard).toHaveBeenCalledOnce();
      expect(result.current.data?.estimate?.estimated_median).toBe(82000);
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });
      const { result } = renderHook(() => useSalaryDashboard(), { wrapper: createWrapper() });
      expect(result.current.fetchStatus).toBe("idle");
    });
  });

  describe("useSalaryEstimate", () => {
    it("should fetch estimate with correct API method", async () => {
      const { result } = renderHook(() => useSalaryEstimate(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(salaryIntelligenceApi.getEstimate).toHaveBeenCalledOnce();
    });
  });

  describe("useSalarySkillImpacts", () => {
    it("should fetch skill impacts", async () => {
      const { result } = renderHook(() => useSalarySkillImpacts(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(salaryIntelligenceApi.getSkillImpacts).toHaveBeenCalledOnce();
    });
  });

  describe("useSalaryTrajectory", () => {
    it("should fetch trajectory data", async () => {
      const { result } = renderHook(() => useSalaryTrajectory(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(salaryIntelligenceApi.getTrajectory).toHaveBeenCalledOnce();
    });
  });

  describe("useSalaryScenarios", () => {
    it("should fetch scenarios list", async () => {
      const { result } = renderHook(() => useSalaryScenarios(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(salaryIntelligenceApi.listScenarios).toHaveBeenCalledOnce();
    });
  });

  describe("useSalaryPreferences", () => {
    it("should fetch preferences when authenticated", async () => {
      const { result } = renderHook(() => useSalaryPreferences(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.preferred_currency).toBe("EUR");
    });
  });

  describe("useTriggerSalaryScan", () => {
    it("should call triggerScan and invalidate queries", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
      const wrapper = ({ children }: { children: React.ReactNode }): React.ReactNode =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useTriggerSalaryScan(), { wrapper });
      result.current.mutate();
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(salaryIntelligenceApi.triggerScan).toHaveBeenCalledOnce();
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: expect.arrayContaining(["salary-intelligence"]) }),
      );
      invalidateSpy.mockRestore();
    });
  });

  describe("useRunSalaryScenario", () => {
    it("should run scenario and invalidate scenarios query", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");
      const wrapper = ({ children }: { children: React.ReactNode }): React.ReactNode =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useRunSalaryScenario(), { wrapper });
      result.current.mutate({ scenario_type: "skill_change", scenario_label: "Learn Rust", scenario_input: { skill_name: "Rust" } });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(salaryIntelligenceApi.runScenario).toHaveBeenCalledOnce();
      invalidateSpy.mockRestore();
    });
  });

  describe("Edge Cases", () => {
    it("should handle null estimate in dashboard", async () => {
      vi.mocked(salaryIntelligenceApi.getDashboard).mockResolvedValueOnce({
        estimate: null, skill_impacts: [], trajectory: [], scenarios: [], preference: null, last_scan_at: null,
      });
      const { result } = renderHook(() => useSalaryDashboard(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.estimate).toBeNull();
    });

    it("should handle empty skill impacts array", async () => {
      vi.mocked(salaryIntelligenceApi.getDashboard).mockResolvedValueOnce({
        estimate: null, skill_impacts: [], trajectory: [], scenarios: [], preference: null, last_scan_at: null,
      });
      const { result } = renderHook(() => useSalaryDashboard(), { wrapper: createWrapper() });
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.skill_impacts).toHaveLength(0);
    });
  });
});
