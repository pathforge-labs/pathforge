/**
 * PathForge — HTTP Core Tests
 * =============================
 * Unit tests for fetchWithAuth, fetchPublic, convenience methods,
 * error handling, and AbortController support.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import {
  mockFetch,
  mockFetchResponse,
  mockNoContentResponse,
  mockErrorResponse,
} from "../test-helpers";

// We must mock token-manager and refresh-queue before importing http
vi.mock("@/lib/token-manager", () => ({
  getAccessToken: vi.fn(() => "mock-access-token"),
}));

vi.mock("@/lib/refresh-queue", () => ({
  refreshAccessToken: vi.fn(),
}));

import {
  fetchWithAuth,
  fetchPublic,
  get,
  post,
  patch,
  put,
  del,
  ApiError,
} from "@/lib/http";
import { getAccessToken } from "@/lib/token-manager";
import { refreshAccessToken } from "@/lib/refresh-queue";

const mockedGetAccessToken = vi.mocked(getAccessToken);
const mockedRefreshAccessToken = vi.mocked(refreshAccessToken);

describe("HTTP Core", () => {
  let fetchMock: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    fetchMock = mockFetch();
    mockedGetAccessToken.mockReturnValue("mock-access-token");
  });

  // ── Authorization Header ──────────────────────────────────

  describe("Authorization header", () => {
    it("should attach Bearer token from token manager", async () => {
      fetchMock.mockResolvedValue(mockFetchResponse({ ok: true }));

      await fetchWithAuth("/api/v1/test");

      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining("/api/v1/test"),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer mock-access-token",
          }),
        }),
      );
    });

    it("should skip auth header when skipAuth is true", async () => {
      fetchMock.mockResolvedValue(mockFetchResponse({ ok: true }));

      await fetchWithAuth("/api/v1/test", { skipAuth: true });

      const callHeaders = fetchMock.mock.calls[0][1].headers as Record<string, string>;
      expect(callHeaders["Authorization"]).toBeUndefined();
    });

    it("should skip auth header when no token is available", async () => {
      mockedGetAccessToken.mockReturnValue(null);
      fetchMock.mockResolvedValue(mockFetchResponse({ ok: true }));

      await fetchWithAuth("/api/v1/test");

      const callHeaders = fetchMock.mock.calls[0][1].headers as Record<string, string>;
      expect(callHeaders["Authorization"]).toBeUndefined();
    });
  });

  // ── Token Refresh on 401 ──────────────────────────────────

  describe("401 token refresh", () => {
    it("should transparently refresh on 401 and retry", async () => {
      const unauthorizedResponse = mockErrorResponse(401, "Token expired");
      const successResponse = mockFetchResponse({ data: "refreshed" });

      fetchMock
        .mockResolvedValueOnce(unauthorizedResponse)
        .mockResolvedValueOnce(successResponse);

      mockedRefreshAccessToken.mockResolvedValue("new-token");

      const result = await fetchWithAuth<{ data: string }>("/api/v1/test");

      expect(mockedRefreshAccessToken).toHaveBeenCalledOnce();
      expect(fetchMock).toHaveBeenCalledTimes(2);
      expect(result.data).toBe("refreshed");
    });

    it("should throw original 401 if refresh fails", async () => {
      const unauthorizedResponse = mockErrorResponse(401, "Token expired");
      fetchMock.mockResolvedValue(unauthorizedResponse);

      mockedRefreshAccessToken.mockRejectedValue(new Error("Refresh failed"));

      await expect(fetchWithAuth("/api/v1/test")).rejects.toThrow(ApiError);
      await expect(fetchWithAuth("/api/v1/test")).rejects.toThrow("Token expired");
    });

    it("should not attempt refresh when skipAuth is true", async () => {
      const unauthorizedResponse = mockErrorResponse(401, "Unauthorized");
      fetchMock.mockResolvedValue(unauthorizedResponse);
      mockedRefreshAccessToken.mockClear();

      await expect(
        fetchWithAuth("/api/v1/test", { skipAuth: true }),
      ).rejects.toThrow(ApiError);

      expect(mockedRefreshAccessToken).not.toHaveBeenCalled();
    });
  });

  // ── Response Handling ─────────────────────────────────────

  describe("Response handling", () => {
    it("should parse JSON response body", async () => {
      const responseData = { id: "1", name: "Test" };
      fetchMock.mockResolvedValue(mockFetchResponse(responseData));

      const result = await fetchWithAuth<{ id: string; name: string }>("/api/v1/test");

      expect(result).toEqual(responseData);
    });

    it("should handle 204 No Content", async () => {
      fetchMock.mockResolvedValue(mockNoContentResponse());

      const result = await fetchWithAuth<void>("/api/v1/test", { method: "DELETE" });

      expect(result).toBeUndefined();
    });
  });

  // ── Error Handling ────────────────────────────────────────

  describe("Error handling", () => {
    it("should parse FastAPI error into ApiError", async () => {
      fetchMock.mockResolvedValue(mockErrorResponse(422, "Validation failed", "VALIDATION_ERROR"));

      try {
        await fetchWithAuth("/api/v1/test");
        expect.fail("Should have thrown");
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        const apiError = error as ApiError;
        expect(apiError.status).toBe(422);
        expect(apiError.code).toBe("VALIDATION_ERROR");
        expect(apiError.message).toBe("Validation failed");
      }
    });

    it("should derive error code from status when not provided", async () => {
      fetchMock.mockResolvedValue(mockErrorResponse(404, "Not found"));

      try {
        await fetchWithAuth("/api/v1/test");
        expect.fail("Should have thrown");
      } catch (error) {
        const apiError = error as ApiError;
        expect(apiError.code).toBe("NOT_FOUND");
      }
    });

    it("should mark 5xx errors as retryable", async () => {
      fetchMock.mockResolvedValue(mockErrorResponse(503, "Service unavailable"));

      try {
        await fetchWithAuth("/api/v1/test");
        expect.fail("Should have thrown");
      } catch (error) {
        const apiError = error as ApiError;
        expect(apiError.isRetryable).toBe(true);
      }
    });

    it("should mark 4xx errors as not retryable", async () => {
      fetchMock.mockResolvedValue(mockErrorResponse(400, "Bad request"));

      try {
        await fetchWithAuth("/api/v1/test");
        expect.fail("Should have thrown");
      } catch (error) {
        const apiError = error as ApiError;
        expect(apiError.isRetryable).toBe(false);
      }
    });
  });

  // ── AbortController (R2) ──────────────────────────────────

  describe("AbortController support", () => {
    it("should forward signal to native fetch", async () => {
      const controller = new AbortController();
      fetchMock.mockResolvedValue(mockFetchResponse({ ok: true }));

      await fetchWithAuth("/api/v1/test", { signal: controller.signal });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          signal: controller.signal,
        }),
      );
    });

    it("should reject with AbortError when aborted", async () => {
      const controller = new AbortController();
      fetchMock.mockImplementation(() => {
        throw new DOMException("The operation was aborted.", "AbortError");
      });

      controller.abort();

      await expect(
        fetchWithAuth("/api/v1/test", { signal: controller.signal }),
      ).rejects.toThrow("The operation was aborted.");
    });
  });

  // ── fetchPublic ───────────────────────────────────────────

  describe("fetchPublic", () => {
    it("should delegate to fetchWithAuth with skipAuth: true", async () => {
      fetchMock.mockResolvedValue(mockFetchResponse({ status: "ok" }));

      await fetchPublic("/api/v1/health");

      const callHeaders = fetchMock.mock.calls[0][1].headers as Record<string, string>;
      expect(callHeaders["Authorization"]).toBeUndefined();
    });
  });

  // ── Convenience Methods ───────────────────────────────────

  describe("Convenience methods", () => {
    it("get() should use GET method", async () => {
      fetchMock.mockResolvedValue(mockFetchResponse({ data: true }));

      await get("/api/v1/test");

      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: "GET" }),
      );
    });

    it("post() should use POST method with body", async () => {
      fetchMock.mockResolvedValue(mockFetchResponse({ id: "1" }));

      await post("/api/v1/test", { name: "Test" });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "POST",
          body: JSON.stringify({ name: "Test" }),
        }),
      );
    });

    it("patch() should use PATCH method with body", async () => {
      fetchMock.mockResolvedValue(mockFetchResponse({ updated: true }));

      await patch("/api/v1/test", { name: "Updated" });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "PATCH",
          body: JSON.stringify({ name: "Updated" }),
        }),
      );
    });

    it("put() should use PUT method with body", async () => {
      fetchMock.mockResolvedValue(mockFetchResponse({ replaced: true }));

      await put("/api/v1/test", { name: "Replaced" });

      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          method: "PUT",
          body: JSON.stringify({ name: "Replaced" }),
        }),
      );
    });

    it("del() should use DELETE method", async () => {
      fetchMock.mockResolvedValue(mockNoContentResponse());

      await del("/api/v1/test/1");

      expect(fetchMock).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({ method: "DELETE" }),
      );
    });
  });
});
