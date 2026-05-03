/**
 * PathForge — HTTP Core
 * ======================
 * Type-safe HTTP client with cookie-first JWT authentication
 * (Track 1 / ADR-0006), transparent token refresh, and standardized
 * error handling.
 *
 * Authentication contract (from 2026-04-25):
 *   1. The browser carries the auth pair in ``httpOnly`` first-party
 *      cookies — JS cannot read them; XSS cannot exfiltrate them.
 *   2. Every request includes ``credentials: "include"`` so the
 *      cookies flow even on cross-origin localhost dev.
 *   3. State-changing requests (POST/PUT/PATCH/DELETE) attach a
 *      ``X-CSRF-Token`` header read from the *non-httpOnly*
 *      ``pathforge_csrf`` cookie. This is the double-submit pattern.
 *   4. The legacy ``Authorization: Bearer`` header is still attached
 *      when ``getAccessToken()`` has a value, so the 30-day overlap
 *      window keeps mid-flight clients working. After day 30 the
 *      auth-provider stops persisting tokens and this branch dies.
 *
 * All API calls MUST go through ``fetchWithAuth()`` — never use raw fetch.
 */

import { refreshAccessToken } from "./refresh-queue";
import { getAccessToken } from "./token-manager";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const CSRF_COOKIE_NAME = "pathforge_csrf";
const CSRF_HEADER_NAME = "X-CSRF-Token";
const MUTATING_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

/**
 * Read the non-httpOnly ``pathforge_csrf`` cookie value.
 *
 * Returns ``null`` on the server (no document) and when the cookie is
 * absent (user not logged in, or pre-Track-1 cookie jar). The caller
 * gates the header attachment on null so unauthenticated requests
 * don't add a stale header.
 */
function readCsrfCookie(): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.match(
    new RegExp("(?:^|; )" + CSRF_COOKIE_NAME + "=([^;]+)"),
  );
  return match ? decodeURIComponent(match[1]) : null;
}

// ── Error Types ─────────────────────────────────────────────

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly details: Record<string, string[]> | null;
  readonly isRetryable: boolean;

  constructor(
    status: number,
    message: string,
    code: string = "UNKNOWN_ERROR",
    details: Record<string, string[]> | null = null,
  ) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
    this.isRetryable = status >= 500;
  }
}

// ── Request Options ─────────────────────────────────────────

export interface RequestOptions extends Omit<RequestInit, "body" | "signal"> {
  /** JSON body to serialize. */
  body?: unknown;
  /** Skip automatic Authorization header attachment. */
  skipAuth?: boolean;
  /** Custom headers to merge with defaults. */
  headers?: Record<string, string>;
  /** AbortSignal for request cancellation. */
  signal?: AbortSignal;
}

// ── Core Fetch ──────────────────────────────────────────────

/**
 * Type-safe fetch wrapper with automatic JWT authentication.
 *
 * - Attaches `Authorization: Bearer <token>` from token manager
 * - On 401: transparently refreshes the token and retries once
 * - Parses error responses into structured `ApiError` instances
 *
 * @param endpoint - API path (e.g., `/api/v1/users/me`)
 * @param options - Request options
 * @returns Parsed JSON response
 * @throws {ApiError} On HTTP errors (4xx, 5xx)
 */
export async function fetchWithAuth<TResponse>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<TResponse> {
  const response = await executeRequest(endpoint, options);

  // Handle 401 — attempt transparent token refresh
  if (response.status === 401 && !options.skipAuth) {
    try {
      await refreshAccessToken();
      // Retry with the new token
      const retryResponse = await executeRequest(endpoint, options);
      return handleResponse<TResponse>(retryResponse);
    } catch {
      // Refresh failed — throw the original 401
      return handleResponse<TResponse>(response);
    }
  }

  return handleResponse<TResponse>(response);
}

/**
 * Unauthenticated fetch — for public endpoints (login, register, health).
 */
export async function fetchPublic<TResponse>(
  endpoint: string,
  options: RequestOptions = {},
): Promise<TResponse> {
  return fetchWithAuth<TResponse>(endpoint, { ...options, skipAuth: true });
}

// ── Convenience Methods ─────────────────────────────────────

export function get<TResponse>(
  endpoint: string,
  options?: RequestOptions,
): Promise<TResponse> {
  return fetchWithAuth<TResponse>(endpoint, { ...options, method: "GET" });
}

export function post<TResponse>(
  endpoint: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<TResponse> {
  return fetchWithAuth<TResponse>(endpoint, { ...options, method: "POST", body });
}

export function patch<TResponse>(
  endpoint: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<TResponse> {
  return fetchWithAuth<TResponse>(endpoint, { ...options, method: "PATCH", body });
}

export function put<TResponse>(
  endpoint: string,
  body?: unknown,
  options?: RequestOptions,
): Promise<TResponse> {
  return fetchWithAuth<TResponse>(endpoint, { ...options, method: "PUT", body });
}

export function del<TResponse = void>(
  endpoint: string,
  options?: RequestOptions,
): Promise<TResponse> {
  return fetchWithAuth<TResponse>(endpoint, { ...options, method: "DELETE" });
}

// ── Internal ────────────────────────────────────────────────

async function executeRequest(
  endpoint: string,
  options: RequestOptions,
): Promise<Response> {
  const url = `${API_BASE_URL}${endpoint}`;

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers ?? {}),
  };

  // Track 1 / ADR-0006: legacy bearer header during the 30-day overlap.
  // The cookie path is the *primary* auth and flows automatically via
  // `credentials: "include"`; this branch only fires for clients that
  // still hold a token in localStorage from before the cookie cutover.
  if (!options.skipAuth) {
    const token = getAccessToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  // Track 1 / ADR-0006: double-submit CSRF on cookie-authenticated
  // mutating requests. We attach the header for any mutating method
  // when the CSRF cookie is present — the server skips the check if
  // an Authorization header is also present (legacy bearer path), so
  // attaching unconditionally is safe and keeps the helper simple.
  const method = (options.method ?? "GET").toUpperCase();
  if (!options.skipAuth && MUTATING_METHODS.has(method)) {
    const csrf = readCsrfCookie();
    if (csrf && !(CSRF_HEADER_NAME in headers)) {
      headers[CSRF_HEADER_NAME] = csrf;
    }
  }

  const { body, skipAuth: _skipAuth, signal, ...fetchOptions } = options; // eslint-disable-line @typescript-eslint/no-unused-vars

  return fetch(url, {
    ...fetchOptions,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
    // Track 1 / ADR-0006: include cookies on every API call so the
    // httpOnly auth cookies flow. Required for cross-origin local dev
    // (localhost:3000 → localhost:8000) — the server's CORS config
    // already includes `allow_credentials=True`.
    credentials: "include",
  });
}

async function handleResponse<TResponse>(response: Response): Promise<TResponse> {
  if (!response.ok) {
    throw await parseApiError(response);
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as TResponse;
  }

  return response.json() as Promise<TResponse>;
}

async function parseApiError(response: Response): Promise<ApiError> {
  try {
    const body = await response.json();

    // FastAPI returns { detail: string | object }
    const message = typeof body.detail === "string"
      ? body.detail
      : typeof body.message === "string"
        ? body.message
        : "An unexpected error occurred";

    const code = typeof body.error_code === "string"
      ? body.error_code
      : deriveErrorCode(response.status);

    const details = typeof body.detail === "object" && !Array.isArray(body.detail)
      ? body.detail as Record<string, string[]>
      : null;

    return new ApiError(response.status, message, code, details);
  } catch {
    return new ApiError(
      response.status,
      response.statusText || "An unexpected error occurred",
      deriveErrorCode(response.status),
    );
  }
}

function deriveErrorCode(status: number): string {
  switch (status) {
    case 400: return "BAD_REQUEST";
    case 401: return "UNAUTHORIZED";
    case 403: return "FORBIDDEN";
    case 404: return "NOT_FOUND";
    case 409: return "CONFLICT";
    case 422: return "VALIDATION_ERROR";
    case 429: return "RATE_LIMITED";
    default: return status >= 500 ? "SERVER_ERROR" : "CLIENT_ERROR";
  }
}
