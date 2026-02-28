/**
 * PathForge Mobile — Refresh Queue
 * ==================================
 * Single-flight token refresh to prevent concurrent refresh calls.
 *
 * When multiple requests get 401 simultaneously, only one refresh
 * call is made. All waiting callers resolve with the same result.
 */

import { fetchPublic } from "./http";
import {
  clearTokens,
  getRefreshToken,
  setTokens,
} from "./token-manager";

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

let refreshPromise: Promise<void> | null = null;

/**
 * Refresh the access token using the stored refresh token.
 * Deduplicates concurrent calls — only one refresh request in flight.
 *
 * @throws On refresh failure (expired refresh token, network error)
 */
export async function refreshAccessToken(): Promise<void> {
  // Return existing promise if refresh is already in progress
  if (refreshPromise !== null) {
    return refreshPromise;
  }

  refreshPromise = executeRefresh();

  try {
    await refreshPromise;
  } finally {
    refreshPromise = null;
  }
}

async function executeRefresh(): Promise<void> {
  const refreshToken = getRefreshToken();

  if (!refreshToken) {
    await clearTokens();
    throw new Error("No refresh token available");
  }

  try {
    const response = await fetchPublic<TokenResponse>(
      "/api/v1/auth/refresh",
      {
        method: "POST",
        body: { refresh_token: refreshToken },
      },
    );

    await setTokens(response.access_token, response.refresh_token);
  } catch {
    // Refresh failed — clear tokens and force re-login
    await clearTokens();
    throw new Error("Token refresh failed");
  }
}
