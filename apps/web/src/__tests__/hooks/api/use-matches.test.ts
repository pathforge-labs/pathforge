/**
 * PathForge — useMatches Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React, { type ReactNode } from "react";

// ── Mocks ──────────────────────────────────────────────────

const { mockUseAuth, mockMatchResume } = vi.hoisted(() => ({
  mockUseAuth: vi.fn<() => { isAuthenticated: boolean }>(),
  mockMatchResume: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({ useAuth: () => mockUseAuth() }));
vi.mock("@/lib/api-client/ai", () => ({ matchResume: mockMatchResume }));

import { matchResume } from "@/lib/api-client/ai";
import { useMatches } from "@/hooks/api/use-matches";

// ── Helpers ────────────────────────────────────────────────

function createWrapper(): ({ children }: { children: ReactNode }) => React.JSX.Element {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function W({ children }: { children: ReactNode }): React.JSX.Element {
    return React.createElement(QueryClientProvider, { client }, children);
  };
}

const MOCK_MATCH_RESPONSE = {
  resume_id: "r1",
  matches: [
    { job_id: "j1", score: 0.92, title: "Senior Engineer", company: "Acme" },
    { job_id: "j2", score: 0.85, title: "Staff Engineer", company: "Beta" },
  ],
  total: 2,
};

// ── Tests ──────────────────────────────────────────────────

describe("useMatches", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  it("does not fetch when resumeId is null", () => {
    const { result } = renderHook(() => useMatches(null), { wrapper: createWrapper() });

    expect(result.current.fetchStatus).toBe("idle");
    expect(matchResume).not.toHaveBeenCalled();
  });

  it("does not fetch when unauthenticated", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false });

    const { result } = renderHook(() => useMatches("r1"), { wrapper: createWrapper() });

    expect(result.current.fetchStatus).toBe("idle");
    expect(matchResume).not.toHaveBeenCalled();
  });

  it("fetches matches when resumeId is set and authenticated", async () => {
    mockMatchResume.mockResolvedValue(MOCK_MATCH_RESPONSE);

    const { result } = renderHook(() => useMatches("r1"), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(matchResume).toHaveBeenCalledWith("r1", 20);
    expect(result.current.data?.matches).toHaveLength(2);
  });

  it("calls matchResume with top_k=20", async () => {
    mockMatchResume.mockResolvedValue(MOCK_MATCH_RESPONSE);

    renderHook(() => useMatches("resume-abc"), { wrapper: createWrapper() });

    await waitFor(() => expect(mockMatchResume).toHaveBeenCalled());
    expect(matchResume).toHaveBeenCalledWith("resume-abc", 20);
  });

  it("surfaces error state on API failure", async () => {
    mockMatchResume.mockRejectedValue(new Error("API down"));

    const { result } = renderHook(() => useMatches("r1"), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
