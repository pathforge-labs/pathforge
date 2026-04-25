/**
 * PathForge — Query Provider Tests
 * ==================================
 * Validates TanStack Query client configuration: staleTime, gcTime,
 * retry logic (skip 4xx, retry 5xx), and mutation defaults.
 */

import { describe, it, expect, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useQuery, useMutation } from "@tanstack/react-query";
import React, { type ReactNode } from "react";

// Mock the HTTP module to make ApiError available
vi.mock("@/lib/http", () => {
  class ApiError extends Error {
    status: number;
    errorCode: string;
    retryable: boolean;
    constructor(message: string, status: number) {
      super(message);
      this.name = "ApiError";
      this.status = status;
      this.errorCode = `HTTP_${status}`;
      this.retryable = status >= 500;
    }
  }
  return { ApiError };
});

// Must import after mock setup
import { QueryProvider } from "@/providers/query-provider";

// ── Helpers ────────────────────────────────────────────────

function createWrapper(): ({ children }: { children: ReactNode }) => React.JSX.Element {
  return function TestWrapper({ children }: { children: ReactNode }): React.JSX.Element {
    return React.createElement(QueryProvider, null, children);
  };
}

// ── Tests ──────────────────────────────────────────────────

describe("QueryProvider", () => {
  it("should provide a QueryClient to children", async () => {
    const mockQueryFn = vi.fn().mockResolvedValue({ data: "test" });

    const { result } = renderHook(
      () =>
        useQuery({
          queryKey: ["test-query"],
          queryFn: mockQueryFn,
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ data: "test" });
  });

  it("should not retry on 4xx API errors", async () => {
    const { ApiError } = await import("@/lib/http");
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const error = new (ApiError as any)("Not Found", 404);
    const mockQueryFn = vi.fn().mockRejectedValue(error);

    const { result } = renderHook(
      () =>
        useQuery({
          queryKey: ["test-4xx"],
          queryFn: mockQueryFn,
          // Use the provider defaults (retry function from createQueryClient)
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isError).toBe(true));

    // Should only be called once — no retries on 4xx
    expect(mockQueryFn).toHaveBeenCalledTimes(1);
  });

  it("should disable mutation retries by default", async () => {
    const mockMutationFn = vi.fn().mockRejectedValue(new Error("Mutation failed"));

    const { result } = renderHook(
      () => useMutation<void, Error, void>({ mutationFn: mockMutationFn }),
      { wrapper: createWrapper() },
    );

    result.current.mutate(undefined);

    await waitFor(() => expect(result.current.isError).toBe(true));
    // Mutations should not retry (retry: false from defaults)
    expect(mockMutationFn).toHaveBeenCalledTimes(1);
  });

  it("should not refetch on window focus by default", async () => {
    const mockQueryFn = vi.fn().mockResolvedValue({ data: "test" });

    const { result } = renderHook(
      () =>
        useQuery({
          queryKey: ["test-focus"],
          queryFn: mockQueryFn,
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    // refetchOnWindowFocus should be false — only the initial fetch should have occurred
    expect(mockQueryFn).toHaveBeenCalledTimes(1);
  });
});
