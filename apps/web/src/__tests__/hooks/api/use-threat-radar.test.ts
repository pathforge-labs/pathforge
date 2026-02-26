/**
 * PathForge — Threat Radar Hooks Tests
 * =======================================
 * Validates TanStack Query hook configuration for Career Threat Radar™:
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
  threatRadarApi: {
    getOverview: vi.fn().mockResolvedValue({
      automation_risk: { overall_risk_score: 35, risk_level: "Low" },
      industry_trends: [],
      skills_shield: null,
      resilience: null,
      alerts_summary: { total: 5, unread: 2 },
      scan_status: "completed",
      last_scan_at: "2026-02-26T12:00:00Z",
    }),
    getResilience: vi.fn().mockResolvedValue({
      overall_score: 72,
      adaptability: 80,
      skill_diversity: 65,
      market_alignment: 70,
      learning_velocity: 75,
      network_strength: 68,
      career_moat_score: 60,
      assessed_at: "2026-02-26T12:00:00Z",
    }),
    getSkillsShield: vi.fn().mockResolvedValue({
      shields: [{ skill_name: "TypeScript", automation_resistance: 85, market_demand: 90, recommendation: "", classification: "shield" }],
      exposures: [{ skill_name: "Data Entry", automation_resistance: 15, market_demand: 20, recommendation: "Upskill", classification: "exposure" }],
      neutrals: [],
      overall_protection_score: 65,
    }),
    getAlerts: vi.fn().mockResolvedValue({
      items: [
        { id: "alert-1", alert_type: "skill_decline", severity: "high", title: "Test Alert", description: "Desc", recommendation: "Act", status: "unread", created_at: "2026-02-26T10:00:00Z", metadata: null },
      ],
      total: 1,
      page: 1,
      per_page: 20,
    }),
    triggerScan: vi.fn().mockResolvedValue({
      scan_id: "scan-1",
      status: "completed",
      automation_risk: { overall_risk_score: 35 },
      industry_trends: [],
      skills_shield: { shields: [], exposures: [], neutrals: [], overall_protection_score: 0 },
      resilience: { overall_score: 70 },
      alerts_generated: 2,
      scanned_at: "2026-02-26T12:00:00Z",
    }),
    updateAlert: vi.fn().mockResolvedValue({
      id: "alert-1",
      status: "read",
    }),
  },
}));

import { threatRadarApi } from "@/lib/api-client";
import {
  useThreatRadarOverview,
  useThreatRadarResilience,
  useThreatRadarSkillsShield,
  useThreatRadarAlerts,
  useTriggerThreatScan,
  useUpdateThreatAlert,
} from "@/hooks/api/use-threat-radar";

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

describe("Threat Radar Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  // ── useThreatRadarOverview ──────────────────────────────

  describe("useThreatRadarOverview", () => {
    it("should fetch overview when authenticated", async () => {
      const { result } = renderHook(() => useThreatRadarOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(threatRadarApi.getOverview).toHaveBeenCalledOnce();
      expect(result.current.data?.automation_risk?.overall_risk_score).toBe(35);
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });

      const { result } = renderHook(() => useThreatRadarOverview(), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(threatRadarApi.getOverview).not.toHaveBeenCalled();
    });

    it("should include alerts summary in response", async () => {
      const { result } = renderHook(() => useThreatRadarOverview(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.alerts_summary.unread).toBe(2);
      expect(result.current.data?.alerts_summary.total).toBe(5);
    });
  });

  // ── useThreatRadarResilience ────────────────────────────

  describe("useThreatRadarResilience", () => {
    it("should fetch resilience data with correct API method", async () => {
      const { result } = renderHook(() => useThreatRadarResilience(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(threatRadarApi.getResilience).toHaveBeenCalledOnce();
      expect(result.current.data?.overall_score).toBe(72);
      expect(result.current.data?.career_moat_score).toBe(60);
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });

      const { result } = renderHook(() => useThreatRadarResilience(), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(threatRadarApi.getResilience).not.toHaveBeenCalled();
    });
  });

  // ── useThreatRadarSkillsShield ──────────────────────────

  describe("useThreatRadarSkillsShield", () => {
    it("should fetch skills shield with shields and exposures", async () => {
      const { result } = renderHook(() => useThreatRadarSkillsShield(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(threatRadarApi.getSkillsShield).toHaveBeenCalledOnce();
      expect(result.current.data?.shields).toHaveLength(1);
      expect(result.current.data?.exposures).toHaveLength(1);
      expect(result.current.data?.overall_protection_score).toBe(65);
    });
  });

  // ── useThreatRadarAlerts ────────────────────────────────

  describe("useThreatRadarAlerts", () => {
    it("should fetch paginated alerts with default parameters", async () => {
      const { result } = renderHook(() => useThreatRadarAlerts(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(threatRadarApi.getAlerts).toHaveBeenCalledWith(1, 20, undefined);
      expect(result.current.data?.items).toHaveLength(1);
    });

    it("should pass custom page and status parameters", async () => {
      const { result } = renderHook(
        () => useThreatRadarAlerts(2, 10, "unread"),
        { wrapper: createWrapper() },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(threatRadarApi.getAlerts).toHaveBeenCalledWith(2, 10, "unread");
    });
  });

  // ── useTriggerThreatScan ────────────────────────────────

  describe("useTriggerThreatScan", () => {
    it("should call triggerScan with soc code and industry", async () => {
      const { result } = renderHook(() => useTriggerThreatScan(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ socCode: "15-1256", industryName: "Technology" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(threatRadarApi.triggerScan).toHaveBeenCalledWith("15-1256", "Technology");
    });

    it("should invalidate all threat-radar queries on success", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useTriggerThreatScan(), { wrapper });

      result.current.mutate({ socCode: "15-1256", industryName: "Technology" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: expect.arrayContaining(["threat-radar"]) }),
      );

      invalidateSpy.mockRestore();
    });
  });

  // ── useUpdateThreatAlert ────────────────────────────────

  describe("useUpdateThreatAlert", () => {
    it("should call updateAlert with alert ID and data", async () => {
      const { result } = renderHook(() => useUpdateThreatAlert(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ alertId: "alert-1", data: { status: "read" } });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(threatRadarApi.updateAlert).toHaveBeenCalledWith("alert-1", { status: "read" });
    });

    it("should invalidate all threat-radar queries on success", async () => {
      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useUpdateThreatAlert(), { wrapper });

      result.current.mutate({ alertId: "alert-1", data: { status: "dismissed" } });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: expect.arrayContaining(["threat-radar"]) }),
      );

      invalidateSpy.mockRestore();
    });
  });
});
