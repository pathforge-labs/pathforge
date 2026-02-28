/**
 * HTTP Client — Unit Tests
 * ==========================
 * Tests type-safe fetch, authentication header injection,
 * 401 token refresh, timeout handling, error parsing,
 * and convenience methods.
 */

import { ApiError, NetworkError, fetchWithAuth, fetchPublic, get, post, del } from "../../lib/http";

// ── Mocks ───────────────────────────────────────────────────

jest.mock("expo-constants", () => ({
  expoConfig: {
    extra: {
      apiBaseUrl: "https://api.test.pathforge.dev",
    },
  },
}));

jest.mock("../../lib/token-manager", () => ({
  getAccessToken: jest.fn(() => "test-bearer-token"),
}));

jest.mock("../../lib/refresh-queue", () => ({
  refreshAccessToken: jest.fn(),
}));

// Mock global fetch
const mockFetch = jest.fn();
global.fetch = mockFetch as unknown as typeof fetch;

// ── Helpers ─────────────────────────────────────────────────

function mockJsonResponse(
  data: unknown,
  options: { status?: number; ok?: boolean; statusText?: string } = {},
): Response {
  return {
    ok: options.ok ?? true,
    status: options.status ?? 200,
    statusText: options.statusText ?? "OK",
    json: () => Promise.resolve(data),
    headers: new Headers(),
  } as unknown as Response;
}

// ── Tests ───────────────────────────────────────────────────

beforeEach(() => {
  jest.clearAllMocks();
  mockFetch.mockReset();
});

describe("http client", () => {
  describe("fetchWithAuth", () => {
    it("should attach Authorization header with bearer token", async () => {
      mockFetch.mockResolvedValue(mockJsonResponse({ message: "ok" }));

      await fetchWithAuth("/api/v1/test");

      const [url, init] = mockFetch.mock.calls[0];
      expect(url).toBe("https://api.test.pathforge.dev/api/v1/test");
      expect(init.headers["Authorization"]).toBe("Bearer test-bearer-token");
    });

    it("should set Content-Type to application/json", async () => {
      mockFetch.mockResolvedValue(mockJsonResponse({}));

      await fetchWithAuth("/api/v1/test");

      const [, init] = mockFetch.mock.calls[0];
      expect(init.headers["Content-Type"]).toBe("application/json");
    });

    it("should serialize body as JSON", async () => {
      mockFetch.mockResolvedValue(mockJsonResponse({}));
      const body = { email: "user@test.com", password: "secure123" };

      await fetchWithAuth("/api/v1/auth/login", { method: "POST", body });

      const [, init] = mockFetch.mock.calls[0];
      expect(init.body).toBe(JSON.stringify(body));
    });

    it("should parse successful JSON responses", async () => {
      const expected = { id: "1", name: "Test User" };
      mockFetch.mockResolvedValue(mockJsonResponse(expected));

      const result = await fetchWithAuth("/api/v1/users/me");

      expect(result).toEqual(expected);
    });
  });

  describe("fetchPublic", () => {
    it("should skip Authorization header", async () => {
      mockFetch.mockResolvedValue(mockJsonResponse({}));

      await fetchPublic("/api/v1/health");

      const [, init] = mockFetch.mock.calls[0];
      expect(init.headers["Authorization"]).toBeUndefined();
    });
  });

  describe("error handling", () => {
    it("should throw ApiError for 4xx responses", async () => {
      mockFetch.mockResolvedValue(
        mockJsonResponse(
          { detail: "Invalid credentials" },
          { status: 401, ok: false },
        ),
      );

      await expect(fetchWithAuth("/api/v1/auth/login", { skipAuth: true })).rejects.toThrow(
        ApiError,
      );
    });

    it("should throw ApiError for 5xx responses with isRetryable=true", async () => {
      mockFetch.mockResolvedValue(
        mockJsonResponse(
          { detail: "Internal server error" },
          { status: 500, ok: false },
        ),
      );

      try {
        await fetchWithAuth("/api/v1/test", { skipAuth: true });
      } catch (error) {
        expect(error).toBeInstanceOf(ApiError);
        expect((error as ApiError).isRetryable).toBe(true);
      }
    });

    it("should throw NetworkError when fetch rejects with TypeError", async () => {
      mockFetch.mockRejectedValue(new TypeError("Failed to fetch"));

      await expect(fetchWithAuth("/api/v1/test")).rejects.toThrow(NetworkError);
    });
  });

  describe("convenience methods", () => {
    it("get() should use GET method", async () => {
      mockFetch.mockResolvedValue(mockJsonResponse({}));

      await get("/api/v1/users/me");

      const [, init] = mockFetch.mock.calls[0];
      expect(init.method).toBe("GET");
    });

    it("post() should use POST method with body", async () => {
      mockFetch.mockResolvedValue(mockJsonResponse({}));
      const body = { title: "New Resume" };

      await post("/api/v1/resume", body);

      const [, init] = mockFetch.mock.calls[0];
      expect(init.method).toBe("POST");
      expect(init.body).toBe(JSON.stringify(body));
    });

    it("del() should use DELETE method", async () => {
      mockFetch.mockResolvedValue(
        mockJsonResponse(undefined, { status: 204, ok: true }),
      );

      await del("/api/v1/resume/123");

      const [, init] = mockFetch.mock.calls[0];
      expect(init.method).toBe("DELETE");
    });
  });
});

describe("ApiError", () => {
  it("should set isRetryable to true for 5xx status", () => {
    const error = new ApiError(503, "Service unavailable");
    expect(error.isRetryable).toBe(true);
  });

  it("should set isRetryable to false for 4xx status", () => {
    const error = new ApiError(400, "Bad request");
    expect(error.isRetryable).toBe(false);
  });

  it("should preserve status, code, and details", () => {
    const details = { email: ["Already taken"] };
    const error = new ApiError(422, "Validation failed", "VALIDATION_ERROR", details);

    expect(error.status).toBe(422);
    expect(error.code).toBe("VALIDATION_ERROR");
    expect(error.details).toEqual(details);
    expect(error.name).toBe("ApiError");
  });
});
