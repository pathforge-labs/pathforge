/**
 * PathForge Mobile — Token Manager
 * ==================================
 * Secure token storage using expo-secure-store (Keychain/Keystore).
 *
 * Unlike web's localStorage-based token manager, SecureStore is
 * asynchronous — all reads/writes are async. An in-memory cache
 * provides synchronous access after initial hydration.
 *
 * All token access MUST go through this module — never use
 * SecureStore directly for auth tokens.
 */

import * as SecureStore from "expo-secure-store";

const ACCESS_TOKEN_KEY = "pathforge_access_token";
const REFRESH_TOKEN_KEY = "pathforge_refresh_token";

type TokenChangeListener = (hasTokens: boolean) => void;

/** In-memory cache for synchronous access after hydration. */
let cachedAccessToken: string | null = null;
let cachedRefreshToken: string | null = null;

/** Whether the initial hydration from SecureStore has completed. */
let hydrated = false;

/** Registered listeners for token change events. */
const listeners: Set<TokenChangeListener> = new Set();

// ── Helpers ─────────────────────────────────────────────────

function notifyListeners(hasTokens: boolean): void {
  listeners.forEach((listener) => {
    try {
      listener(hasTokens);
    } catch {
      // Prevent listener errors from breaking token operations
    }
  });
}

// ── Initialization ──────────────────────────────────────────

/**
 * Hydrate in-memory cache from SecureStore.
 * Must be called once on app startup before any auth decisions.
 */
export async function hydrateTokens(): Promise<void> {
  try {
    cachedAccessToken = await SecureStore.getItemAsync(ACCESS_TOKEN_KEY);
    cachedRefreshToken = await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
  } catch {
    // SecureStore unavailable — clear cache
    cachedAccessToken = null;
    cachedRefreshToken = null;
  }
  hydrated = true;
}

// ── Public API ──────────────────────────────────────────────

/** Returns true if initial hydration from SecureStore is complete. */
export function isHydrated(): boolean {
  return hydrated;
}

/** Get cached access token (synchronous after hydration). */
export function getAccessToken(): string | null {
  return cachedAccessToken;
}

/** Get cached refresh token (synchronous after hydration). */
export function getRefreshToken(): string | null {
  return cachedRefreshToken;
}

/** Persist both tokens to SecureStore and update cache. */
export async function setTokens(
  accessToken: string,
  refreshToken: string,
): Promise<void> {
  cachedAccessToken = accessToken;
  cachedRefreshToken = refreshToken;

  try {
    await SecureStore.setItemAsync(ACCESS_TOKEN_KEY, accessToken);
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, refreshToken);
  } catch {
    // SecureStore write failed — in-memory cache still updated
  }

  notifyListeners(true);
}

/** Clear both tokens from SecureStore and cache. */
export async function clearTokens(): Promise<void> {
  cachedAccessToken = null;
  cachedRefreshToken = null;

  try {
    await SecureStore.deleteItemAsync(ACCESS_TOKEN_KEY);
    await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
  } catch {
    // Silently fail — cache is already cleared
  }

  notifyListeners(false);
}

/** Check if tokens exist in cache. */
export function hasTokens(): boolean {
  return cachedAccessToken !== null;
}

/**
 * Subscribe to token change events (login/logout).
 * Returns an unsubscribe function.
 */
export function onTokenChange(listener: TokenChangeListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
