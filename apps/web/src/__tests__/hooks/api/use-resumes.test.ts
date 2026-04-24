/**
 * PathForge — useResumes Hook Tests
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React, { type ReactNode } from "react";

// ── Mocks ──────────────────────────────────────────────────

const { mockUseAuth, mockList } = vi.hoisted(() => ({
  mockUseAuth: vi.fn<() => { isAuthenticated: boolean }>(),
  mockList: vi.fn(),
}));

vi.mock("@/hooks/use-auth", () => ({ useAuth: () => mockUseAuth() }));
vi.mock("@/lib/api-client", () => ({ resumesApi: { list: mockList } }));

import { resumesApi } from "@/lib/api-client";
import { useResumes } from "@/hooks/api/use-resumes";

// ── Helpers ────────────────────────────────────────────────

function createWrapper(): ({ children }: { children: ReactNode }) => React.JSX.Element {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return function W({ children }: { children: ReactNode }): React.JSX.Element {
    return React.createElement(QueryClientProvider, { client }, children);
  };
}

// ── Tests ──────────────────────────────────────────────────

describe("useResumes", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseAuth.mockReturnValue({ isAuthenticated: true });
  });

  it("fetches resume list when authenticated", async () => {
    const resumes = [
      { id: "r1", title: "My CV", version: 1, raw_text_length: 500,
        has_structured_data: true, has_embedding: true, created_at: "2026-01-01T00:00:00Z" },
    ];
    mockList.mockResolvedValue(resumes);

    const { result } = renderHook(() => useResumes(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(resumesApi.list).toHaveBeenCalledOnce();
    expect(result.current.data).toEqual(resumes);
  });

  it("does not fetch when unauthenticated", () => {
    mockUseAuth.mockReturnValue({ isAuthenticated: false });

    const { result } = renderHook(() => useResumes(), { wrapper: createWrapper() });

    expect(result.current.fetchStatus).toBe("idle");
    expect(resumesApi.list).not.toHaveBeenCalled();
  });

  it("returns error state on API failure", async () => {
    mockList.mockRejectedValue(new Error("Network error"));

    const { result } = renderHook(() => useResumes(), { wrapper: createWrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.data).toBeUndefined();
  });
});
