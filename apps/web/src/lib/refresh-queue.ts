/**
 * PathForge — Refresh Queue
 * ==========================
 * Single-flight token refresh mechanism.
 *
 * When a 401 is detected, this module ensures only ONE refresh call
 * is made. All concurrent requests are queued and replayed once the
 * new token is available. On refresh failure, all queued requests
 * are rejected and the user is redirected to login.
 */

import { clearTokens, getRefreshToken, setTokens } from "./token-manager";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface QueuedRequest {
  resolve: (token: string) => void;
  reject: (error: Error) => void;
}

let isRefreshing = false;
let refreshQueue: QueuedRequest[] = [];

/**
 * Attempt to refresh the access token.
 *
 * - If a refresh is already in progress, returns a promise that resolves
 *   when the in-flight refresh completes.
 * - If no refresh is in progress, initiates one. On success, all queued
 *   requests receive the new token. On failure, all are rejected.
 *
 * @returns The new access token.
 * @throws {Error} If refresh fails (expired, revoked, network error).
 */
export async function refreshAccessToken(): Promise<string> {
  if (isRefreshing) {
    // A refresh is already in-flight — queue this caller
    return new Promise<string>((resolve, reject) => {
      refreshQueue.push({ resolve, reject });
    });
  }

  isRefreshing = true;

  try {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
      throw new Error("No refresh token available");
    }

    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      const body = await response.json().catch(() => ({ detail: "Token refresh failed" }));
      throw new Error(body.detail ?? "Token refresh failed");
    }

    const data: { access_token: string; refresh_token: string } = await response.json();

    // Store new token pair
    setTokens(data.access_token, data.refresh_token);

    // Resolve all queued requests with the new access token
    processQueue(null, data.access_token);

    return data.access_token;
  } catch (error) {
    // Refresh failed — clear all tokens and reject queued requests
    clearTokens();
    const refreshError = error instanceof Error
      ? error
      : new Error("Token refresh failed");
    processQueue(refreshError, null);
    throw refreshError;
  } finally {
    isRefreshing = false;
  }
}

/**
 * Check whether a token refresh is currently in progress.
 */
export function isRefreshInProgress(): boolean {
  return isRefreshing;
}

// ── Internal ────────────────────────────────────────────────

function processQueue(error: Error | null, token: string | null): void {
  const queue = [...refreshQueue];
  refreshQueue = [];

  for (const request of queue) {
    if (error) {
      request.reject(error);
    } else if (token) {
      request.resolve(token);
    }
  }
}
