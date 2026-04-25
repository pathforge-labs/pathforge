/**
 * PathForge — User Profile Hooks Tests
 * =======================================
 * Validates TanStack Query hook configuration for user profile operations:
 * auth gating, mutation delegation, query invalidation.
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
  userProfileApi: {
    getProfile: vi.fn().mockResolvedValue({ id: "profile-1", headline: "Engineer" }),
    getOnboardingStatus: vi.fn().mockResolvedValue({
      profile_complete: true,
      resume_uploaded: true,
      career_dna_generated: false,
      steps_completed: 2,
      total_steps: 4,
    }),
    updateProfile: vi.fn().mockResolvedValue({ id: "profile-1", headline: "Senior Engineer" }),
    requestExport: vi.fn().mockResolvedValue({ id: "export-1", status: "pending" }),
  },
}));

import { userProfileApi } from "@/lib/api-client";
import {
  useUserProfile,
  useOnboardingStatus,
  useUpdateProfile,
  useRequestDataExport,
} from "@/hooks/api/use-user-profile";

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

describe("User Profile Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  // ── useUserProfile ─────────────────────────────────────

  describe("useUserProfile", () => {
    it("should fetch profile when authenticated", async () => {
      const { result } = renderHook(() => useUserProfile(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(userProfileApi.getProfile).toHaveBeenCalledOnce();
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });

      const { result } = renderHook(() => useUserProfile(), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(userProfileApi.getProfile).not.toHaveBeenCalled();
    });
  });

  // ── useOnboardingStatus ────────────────────────────────

  describe("useOnboardingStatus", () => {
    it("should fetch onboarding status when authenticated", async () => {
      const { result } = renderHook(() => useOnboardingStatus(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(userProfileApi.getOnboardingStatus).toHaveBeenCalledOnce();
    });

    it("should not fetch when unauthenticated", () => {
      mockUseAuth.mockReturnValue({ isAuthenticated: false });

      const { result } = renderHook(() => useOnboardingStatus(), {
        wrapper: createWrapper(),
      });

      expect(result.current.fetchStatus).toBe("idle");
      expect(userProfileApi.getOnboardingStatus).not.toHaveBeenCalled();
    });
  });

  // ── useUpdateProfile ───────────────────────────────────

  describe("useUpdateProfile", () => {
    it("should call updateProfile with data", async () => {
      const { result } = renderHook(() => useUpdateProfile(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ headline: "Senior Engineer" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(userProfileApi.updateProfile).toHaveBeenCalledWith({ headline: "Senior Engineer" });
    });

    it("should invalidate user-profile queries on success", async () => {
      const queryClient = createTestQueryClient();
      queryClient.setQueryData(["user-profile", "profile"], { stale: true });

      const invalidateSpy = vi.spyOn(queryClient, "invalidateQueries");

      const wrapper = ({ children }: { children: ReactNode }) =>
        React.createElement(QueryClientProvider, { client: queryClient }, children as React.ReactNode);

      const { result } = renderHook(() => useUpdateProfile(), { wrapper });

      result.current.mutate({ headline: "Updated" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith(
        expect.objectContaining({ queryKey: expect.arrayContaining(["user-profile"]) }),
      );

      invalidateSpy.mockRestore();
    });
  });

  // ── useRequestDataExport ───────────────────────────────

  describe("useRequestDataExport", () => {
    it("should call requestExport with format", async () => {
      const { result } = renderHook(() => useRequestDataExport(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ export_format: "json" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(userProfileApi.requestExport).toHaveBeenCalledWith({ export_format: "json" });
    });
  });
});
