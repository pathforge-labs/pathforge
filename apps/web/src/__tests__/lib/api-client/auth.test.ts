/**
 * PathForge — Auth API Client Tests
 * ====================================
 * Unit tests verifying authApi calls correct endpoints
 * with proper HTTP methods and request bodies.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { mockFetchResponse } from "../../test-helpers";

// Mock HTTP layer — we test endpoint correctness, not HTTP mechanics
vi.mock("@/lib/http", () => ({
  fetchWithAuth: vi.fn(),
  fetchPublic: vi.fn(),
}));

import { authApi } from "@/lib/api-client/auth";
import { fetchPublic, fetchWithAuth } from "@/lib/http";

const mockedFetchPublic = vi.mocked(fetchPublic);
const mockedFetchWithAuth = vi.mocked(fetchWithAuth);

describe("Auth API Client", () => {
  beforeEach(() => {
    mockedFetchPublic.mockResolvedValue(
      mockFetchResponse({ access_token: "token", refresh_token: "refresh" }),
    );
    mockedFetchWithAuth.mockResolvedValue(undefined);
  });

  it("login should POST to /api/v1/auth/login with credentials", async () => {
    await authApi.login({ email: "user@test.com", password: "pass123" });

    expect(mockedFetchPublic).toHaveBeenCalledWith(
      "/api/v1/auth/login",
      expect.objectContaining({
        method: "POST",
        body: { email: "user@test.com", password: "pass123" },
      }),
    );
  });

  it("register should POST to /api/v1/auth/register with user data", async () => {
    await authApi.register({
      email: "new@test.com",
      password: "pass123",
      full_name: "Test User",
    });

    expect(mockedFetchPublic).toHaveBeenCalledWith(
      "/api/v1/auth/register",
      expect.objectContaining({
        method: "POST",
        body: {
          email: "new@test.com",
          password: "pass123",
          full_name: "Test User",
        },
      }),
    );
  });

  it("refresh should POST to /api/v1/auth/refresh with refresh token", async () => {
    await authApi.refresh("refresh-token-123");

    expect(mockedFetchPublic).toHaveBeenCalledWith(
      "/api/v1/auth/refresh",
      expect.objectContaining({
        method: "POST",
        body: { refresh_token: "refresh-token-123" },
      }),
    );
  });

  it("logout should POST to /api/v1/auth/logout", async () => {
    await authApi.logout();

    expect(mockedFetchWithAuth).toHaveBeenCalledWith(
      "/api/v1/auth/logout",
      expect.objectContaining({ method: "POST" }),
    );
  });
});
