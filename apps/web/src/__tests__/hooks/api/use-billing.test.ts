/**
 * PathForge — Billing Hooks Tests
 * ==================================
 * Sprint 35 (I4): Tests for billing domain React Query hooks.
 *
 * Follows established PathForge hook test pattern:
 * - vi.mock for API client modules
 * - createWrapper with QueryClientProvider
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

// ── Mocks ──────────────────────────────────────────────────

vi.mock("@/lib/api-client", () => ({
  billingApi: {
    getSubscription: vi.fn().mockResolvedValue({
      id: "sub-1",
      user_id: "user-1",
      tier: "free",
      status: "active",
      stripe_customer_id: null,
      stripe_subscription_id: null,
      current_period_start: null,
      current_period_end: null,
      cancel_at_period_end: false,
    }),
    getUsage: vi.fn().mockResolvedValue({
      tier: "free",
      scans_used: 1,
      scans_limit: 3,
      period_start: "2024-01-01T00:00:00Z",
      period_end: "2024-02-01T00:00:00Z",
    }),
    getFeatures: vi.fn().mockResolvedValue({
      tier: "free",
      engines: ["career_dna", "threat_radar"],
      scan_limit: 3,
      billing_enabled: false,
    }),
    getFeaturesPublic: vi.fn().mockResolvedValue({
      tier: "free",
      engines: ["career_dna", "threat_radar"],
      scan_limit: 3,
      billing_enabled: false,
    }),
    createCheckout: vi.fn().mockResolvedValue({
      checkout_url: "https://checkout.stripe.com/test",
    }),
    createPortal: vi.fn().mockResolvedValue({
      portal_url: "https://billing.stripe.com/portal/test",
    }),
  },
}));

// Mock brand config for APP_URL used in useCreateCheckout
vi.mock("@/config/brand", () => ({
  APP_URL: "http://localhost:3000",
  APP_NAME: "PathForge",
  pageTitle: (title: string) => `${title} | PathForge`,
}));

import { billingApi } from "@/lib/api-client";
import {
  useSubscription,
  useUsage,
  useFeatures,
  useCreateCheckout,
  useCreatePortal,
} from "@/hooks/api/use-billing";

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

describe("Billing Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ── useSubscription ─────────────────────────────────────

  describe("useSubscription", () => {
    it("should fetch subscription data", async () => {
      const { result } = renderHook(() => useSubscription(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(billingApi.getSubscription).toHaveBeenCalledOnce();
      expect(result.current.data?.tier).toBe("free");
      expect(result.current.data?.status).toBe("active");
    });
  });

  // ── useUsage ────────────────────────────────────────────

  describe("useUsage", () => {
    it("should fetch usage summary with scan counts", async () => {
      const { result } = renderHook(() => useUsage(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(billingApi.getUsage).toHaveBeenCalledOnce();
      expect(result.current.data?.scans_used).toBe(1);
      expect(result.current.data?.scans_limit).toBe(3);
    });
  });

  // ── useFeatures ─────────────────────────────────────────

  describe("useFeatures", () => {
    it("should fetch feature access with engine list", async () => {
      const { result } = renderHook(() => useFeatures(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(billingApi.getFeatures).toHaveBeenCalledOnce();
      expect(result.current.data?.engines).toContain("career_dna");
      expect(result.current.data?.engines).toContain("threat_radar");
      expect(result.current.data?.billing_enabled).toBe(false);
    });
  });

  // ── useCreateCheckout ───────────────────────────────────

  describe("useCreateCheckout", () => {
    it("should call createCheckout with tier and interval", async () => {
      // Mock window.location to prevent redirect
      const locationSpy = vi.spyOn(window, "location", "get").mockReturnValue({
        ...window.location,
        href: "",
      });

      const { result } = renderHook(() => useCreateCheckout(), {
        wrapper: createWrapper(),
      });

      result.current.mutate({ tier: "pro" });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(billingApi.createCheckout).toHaveBeenCalledOnce();

      locationSpy.mockRestore();
    });
  });

  // ── useCreatePortal ─────────────────────────────────────

  describe("useCreatePortal", () => {
    it("should call createPortal on mutate", async () => {
      const locationSpy = vi.spyOn(window, "location", "get").mockReturnValue({
        ...window.location,
        href: "",
      });

      const { result } = renderHook(() => useCreatePortal(), {
        wrapper: createWrapper(),
      });

      result.current.mutate();

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(billingApi.createPortal).toHaveBeenCalledOnce();

      locationSpy.mockRestore();
    });
  });
});
