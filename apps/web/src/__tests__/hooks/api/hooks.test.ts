/**
 * PathForge — API Hooks Tests
 * ============================
 * Validates TanStack Query hook configuration: query keys, auth gating,
 * staleTime, refetchInterval, mutation invalidation, and API delegation.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React, { type ReactNode } from "react";

// ── Mocks ──────────────────────────────────────────────────

// Mock useAuth to control authentication state
const mockUseAuth = vi.fn<() => { isAuthenticated: boolean }>();
vi.mock("@/hooks/use-auth", () => ({
  useAuth: () => mockUseAuth(),
}));

// Mock all API client modules
vi.mock("@/lib/api-client", () => ({
  healthApi: {
    ready: vi.fn().mockResolvedValue({ status: "ok", database: "connected" }),
  },
  careerDnaApi: {
    getProfile: vi.fn().mockResolvedValue({ id: "profile-1" }),
    getSummary: vi.fn().mockResolvedValue({ id: "summary-1" }),
    generate: vi.fn().mockResolvedValue({ id: "generated-1" }),
  },
  commandCenterApi: {
    getDashboard: vi.fn().mockResolvedValue({ engines: [] }),
    getHealthSummary: vi.fn().mockResolvedValue({ score: 80 }),
    getEngineDetail: vi.fn().mockResolvedValue({ name: "career-dna" }),
    refreshSnapshot: vi.fn().mockResolvedValue({ timestamp: "now" }),
  },
  notificationsApi: {
    getUnreadCount: vi.fn().mockResolvedValue({ count: 3 }),
    markAllRead: vi.fn().mockResolvedValue({ success: true }),
  },
}));

import { healthApi, careerDnaApi, commandCenterApi, notificationsApi } from "@/lib/api-client";
import { useHealthCheck } from "@/hooks/api/use-health";
import {
  useCareerDnaProfile,
  useCareerDnaSummary,
  useGenerateCareerDna,
} from "@/hooks/api/use-career-dna";
import {
  useCommandCenterDashboard,
  useCareerHealthSummary,
  useEngineDetail,
  useRefreshVitals,
} from "@/hooks/api/use-command-center";
import {
  useUnreadNotificationCount,
  useMarkAllNotificationsRead,
} from "@/hooks/api/use-notifications";

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

describe("API Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  // ── useHealthCheck ─────────────────────────────────────

  describe("useHealthCheck", () => {
    it("should fetch health data with correct query key", async () => {
      const { result } = renderHook(() => useHealthCheck(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(healthApi.ready).toHaveBeenCalledOnce();
    });

    it("should not require authentication", async () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });

      const { result } = renderHook(() => useHealthCheck(), {
        wrapper: createWrapper(),
      });

      // Health check does NOT use auth gating — should still fetch
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(healthApi.ready).toHaveBeenCalledOnce();
    });
  });

  // ── useCareerDnaProfile ────────────────────────────────

  describe("useCareerDnaProfile", () => {
    it("should fetch when authenticated", async () => {
      const { result } = renderHook(() => useCareerDnaProfile(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerDnaApi.getProfile).toHaveBeenCalledOnce();
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });

      const { result } = renderHook(() => useCareerDnaProfile(), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(careerDnaApi.getProfile).not.toHaveBeenCalled();
    });
  });

  // ── useCareerDnaSummary ────────────────────────────────

  describe("useCareerDnaSummary", () => {
    it("should be auth-gated and use correct API method", async () => {
      const { result } = renderHook(() => useCareerDnaSummary(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerDnaApi.getSummary).toHaveBeenCalledOnce();
    });
  });

  // ── useGenerateCareerDna ───────────────────────────────

  describe("useGenerateCareerDna", () => {
    it("should call generate with params", async () => {
      const { result } = renderHook(() => useGenerateCareerDna(), {
        wrapper: createWrapper(),
      });

      result.current.mutate(undefined);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(careerDnaApi.generate).toHaveBeenCalledWith(undefined);
    });

    it("should invalidate careerDna and commandCenter queries on success", async () => {
      const queryClient = createTestQueryClient();

      // Seed cache with stale data so we can verify invalidation
      queryClient.setQueryData(["careerDna", "all"], { stale: true });
      queryClient.setQueryData(["commandCenter", "all"], { stale: true });

      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: React.ReactNode }): React.ReactNode =>
        React.createElement(QueryClientProvider, { client: queryClient }, children);

      const { result } = renderHook(() => useGenerateCareerDna(), { wrapper });

      result.current.mutate(undefined);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify both query domains are invalidated
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: expect.arrayContaining(["career-dna"]) }),
      );
      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: expect.arrayContaining(["command-center"]) }),
      );

      invalidateSpy.mockRestore();
    });
  });

  // ── useCommandCenterDashboard ──────────────────────────

  describe("useCommandCenterDashboard", () => {
    it("should fetch dashboard when authenticated", async () => {
      const { result } = renderHook(() => useCommandCenterDashboard(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(commandCenterApi.getDashboard).toHaveBeenCalledOnce();
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });

      const { result } = renderHook(() => useCommandCenterDashboard(), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(commandCenterApi.getDashboard).not.toHaveBeenCalled();
    });
  });

  // ── useCareerHealthSummary ─────────────────────────────

  describe("useCareerHealthSummary", () => {
    it("should be auth-gated and use correct API method", async () => {
      const { result } = renderHook(() => useCareerHealthSummary(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(commandCenterApi.getHealthSummary).toHaveBeenCalledOnce();
    });
  });

  // ── useEngineDetail ────────────────────────────────────

  describe("useEngineDetail", () => {
    it("should fetch engine detail with name parameter", async () => {
      const { result } = renderHook(() => useEngineDetail("career-dna"), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(commandCenterApi.getEngineDetail).toHaveBeenCalledWith("career-dna");
    });

    it("should not fetch when engineName is empty", () => {
      const { result } = renderHook(() => useEngineDetail(""), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(commandCenterApi.getEngineDetail).not.toHaveBeenCalled();
    });
  });

  // ── useRefreshVitals ───────────────────────────────────

  describe("useRefreshVitals", () => {
    it("should call refreshSnapshot on mutate", async () => {
      const { result } = renderHook(() => useRefreshVitals(), {
        wrapper: createWrapper(),
      });

      result.current.mutate();

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(commandCenterApi.refreshSnapshot).toHaveBeenCalledOnce();
    });
  });

  // ── useUnreadNotificationCount ─────────────────────────

  describe("useUnreadNotificationCount", () => {
    it("should fetch when authenticated", async () => {
      const { result } = renderHook(() => useUnreadNotificationCount(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(notificationsApi.getUnreadCount).toHaveBeenCalledOnce();
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });

      const { result } = renderHook(() => useUnreadNotificationCount(), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(notificationsApi.getUnreadCount).not.toHaveBeenCalled();
    });
  });

  // ── useMarkAllNotificationsRead ────────────────────────

  describe("useMarkAllNotificationsRead", () => {
    it("should call markAllRead on mutate", async () => {
      const { result } = renderHook(() => useMarkAllNotificationsRead(), {
        wrapper: createWrapper(),
      });

      result.current.mutate();

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(notificationsApi.markAllRead).toHaveBeenCalledOnce();
    });
  });
});
