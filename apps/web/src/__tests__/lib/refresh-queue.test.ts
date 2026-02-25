/**
 * PathForge — Refresh Queue Tests
 * =================================
 * Unit tests for single-flight token refresh mechanism.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mockFetch, mockFetchResponse, mockErrorResponse } from "../test-helpers";

// Mock token-manager before importing refresh-queue
vi.mock("@/lib/token-manager", () => ({
  getRefreshToken: vi.fn(() => "mock-refresh-token"),
  setTokens: vi.fn(),
  clearTokens: vi.fn(),
}));

import {
  refreshAccessToken,
  isRefreshInProgress,
} from "@/lib/refresh-queue";
import { getRefreshToken, setTokens, clearTokens } from "@/lib/token-manager";

const mockedGetRefreshToken = vi.mocked(getRefreshToken);
const mockedSetTokens = vi.mocked(setTokens);
const mockedClearTokens = vi.mocked(clearTokens);

describe("Refresh Queue", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = mockFetch();
    mockedGetRefreshToken.mockReturnValue("mock-refresh-token");
    mockedSetTokens.mockClear();
    mockedClearTokens.mockClear();
  });

  // ── Successful Refresh ────────────────────────────────────

  describe("Successful refresh", () => {
    it("should store new tokens on success", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({
          access_token: "new-access",
          refresh_token: "new-refresh",
        }),
      );

      const token = await refreshAccessToken();

      expect(token).toBe("new-access");
      expect(mockedSetTokens).toHaveBeenCalledWith("new-access", "new-refresh");
    });

    it("should POST to /api/v1/auth/refresh with refresh token", async () => {
      fetchMock.mockResolvedValue(
        mockFetchResponse({
          access_token: "new-access",
          refresh_token: "new-refresh",
        }),
      );

      await refreshAccessToken();

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/auth/refresh"),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ refresh_token: "mock-refresh-token" }),
        }),
      );
    });
  });

  // ── Failed Refresh ────────────────────────────────────────

  describe("Failed refresh", () => {
    it("should clear tokens when refresh fails", async () => {
      fetchMock.mockResolvedValue(mockErrorResponse(401, "Token expired"));

      await expect(refreshAccessToken()).rejects.toThrow();
      expect(mockedClearTokens).toHaveBeenCalled();
    });

    it("should throw when no refresh token is available", async () => {
      mockedGetRefreshToken.mockReturnValue(null);

      await expect(refreshAccessToken()).rejects.toThrow("No refresh token available");
      expect(mockedClearTokens).toHaveBeenCalled();
    });
  });

  // ── Single-Flight Queueing ────────────────────────────────

  describe("Single-flight queueing", () => {
    it("should only make one fetch call for concurrent requests", async () => {
      // Use a deferred promise to control timing
      let resolveRefresh: (value: Response) => void;
      const pendingRefresh = new Promise<Response>((resolve) => {
        resolveRefresh = resolve;
      });

      fetchMock.mockReturnValue(pendingRefresh);

      // Fire 3 concurrent refresh requests
      const promise1 = refreshAccessToken();
      const promise2 = refreshAccessToken();
      const promise3 = refreshAccessToken();

      // Resolve the single fetch call
      resolveRefresh!(
        mockFetchResponse({
          access_token: "shared-access",
          refresh_token: "shared-refresh",
        }),
      );

      const [token1, token2, token3] = await Promise.all([
        promise1,
        promise2,
        promise3,
      ]);

      // All three should get the same token
      expect(token1).toBe("shared-access");
      expect(token2).toBe("shared-access");
      expect(token3).toBe("shared-access");

      // But only one fetch call should have been made
      expect(fetchMock).toHaveBeenCalledTimes(1);
    });

    it("should reject all queued promises on failure", async () => {
      let rejectRefresh: (reason: Response) => void;
      const pendingRefresh = new Promise<Response>((_resolve, reject) => {
        rejectRefresh = reject;
      });
      // Simulate a failed fetch by returning a rejected promise
      fetchMock.mockReturnValue(pendingRefresh);

      const promise1 = refreshAccessToken();
      const promise2 = refreshAccessToken();

      rejectRefresh!(mockErrorResponse(401, "Invalid token"));

      await expect(promise1).rejects.toThrow();
      await expect(promise2).rejects.toThrow();
    });
  });

  // ── State ─────────────────────────────────────────────────

  describe("isRefreshInProgress", () => {
    it("should return false when idle", () => {
      expect(isRefreshInProgress()).toBe(false);
    });
  });
});
