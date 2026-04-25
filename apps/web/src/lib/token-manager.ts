/**
 * PathForge — Token Manager
 * ==========================
 * Centralized token storage with in-memory cache, localStorage
 * persistence, SSR safety, and multi-tab synchronization.
 *
 * All token access MUST go through this module — never read/write
 * localStorage directly for auth tokens.
 */

const ACCESS_TOKEN_KEY = "pathforge_access_token";
const REFRESH_TOKEN_KEY = "pathforge_refresh_token";

type TokenChangeListener = (hasTokens: boolean) => void;

/** In-memory cache for current-tab performance. */
let cachedAccessToken: string | null = null;
let cachedRefreshToken: string | null = null;

/** Registered listeners for token change events. */
const listeners: Set<TokenChangeListener> = new Set();

// ── Helpers ─────────────────────────────────────────────────

function isBrowser(): boolean {
  return typeof window !== "undefined";
}

function readFromStorage(key: string): string | null {
  if (!isBrowser()) return null;
  try {
    return localStorage.getItem(key);
  } catch {
    // localStorage unavailable (incognito, storage quota, etc.)
    return null;
  }
}

function writeToStorage(key: string, value: string): void {
  if (!isBrowser()) return;
  try {
    localStorage.setItem(key, value);
  } catch {
    // Silently fail — in-memory cache remains the source of truth
  }
}

function removeFromStorage(key: string): void {
  if (!isBrowser()) return;
  try {
    localStorage.removeItem(key);
  } catch {
    // Silently fail
  }
}

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

/** Hydrate in-memory cache from localStorage on module load. */
function hydrateFromStorage(): void {
  cachedAccessToken = readFromStorage(ACCESS_TOKEN_KEY);
  cachedRefreshToken = readFromStorage(REFRESH_TOKEN_KEY);
}

if (isBrowser()) {
  hydrateFromStorage();

  /**
   * Multi-tab synchronization: listen for storage changes from other tabs.
   * When another tab clears tokens (logout), this tab detects the change.
   */
  window.addEventListener("storage", (event: StorageEvent) => {
    if (event.key === ACCESS_TOKEN_KEY || event.key === REFRESH_TOKEN_KEY) {
      hydrateFromStorage();
      notifyListeners(cachedAccessToken !== null);
    }
  });
}

// ── Public API ──────────────────────────────────────────────

export function getAccessToken(): string | null {
  return cachedAccessToken;
}

export function getRefreshToken(): string | null {
  return cachedRefreshToken;
}

export function setTokens(accessToken: string, refreshToken: string): void {
  cachedAccessToken = accessToken;
  cachedRefreshToken = refreshToken;
  writeToStorage(ACCESS_TOKEN_KEY, accessToken);
  writeToStorage(REFRESH_TOKEN_KEY, refreshToken);
  notifyListeners(true);
}

export function clearTokens(): void {
  cachedAccessToken = null;
  cachedRefreshToken = null;
  removeFromStorage(ACCESS_TOKEN_KEY);
  removeFromStorage(REFRESH_TOKEN_KEY);
  notifyListeners(false);
}

export function hasTokens(): boolean {
  return cachedAccessToken !== null;
}

/**
 * Subscribe to token change events (login/logout/cross-tab sync).
 * Returns an unsubscribe function.
 */
export function onTokenChange(listener: TokenChangeListener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}
