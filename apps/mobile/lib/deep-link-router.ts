/**
 * PathForge Mobile — Deep Link Router
 * ======================================
 * Centralized route mapping and validation for push notification
 * deep links. All incoming action_url values are validated against
 * a whitelist before navigation.
 *
 * Sprint 33 — WS-3: Deep Link Handler Hardening
 */

// ── Route Map ───────────────────────────────────────────────

/**
 * Maps backend `action_url` values → Expo Router paths.
 * Only tab/home routes are supported — auth routes excluded
 * because AuthGate in _layout.tsx handles auth redirects.
 */
const DEEP_LINK_ROUTES: Readonly<Record<string, string>> = {
  "/career-dna": "/(tabs)/home/career-dna",
  "/threat-radar": "/(tabs)/home",
  "/notifications": "/(tabs)/notifications",
  "/settings": "/(tabs)/settings",
  "/dashboard": "/(tabs)/home",
} as const;

/** Safe fallback route when action_url is unrecognized. */
export const DEFAULT_ROUTE = "/(tabs)/home";

// ── Types ───────────────────────────────────────────────────

export interface DeepLinkResult {
  /** Whether the action_url matched a known route. */
  readonly resolved: boolean;
  /** The Expo Router path to navigate to. */
  readonly route: string;
  /** The original action_url from the push payload. */
  readonly originalUrl: string;
}

// ── Public API ──────────────────────────────────────────────

/**
 * Resolve a push notification action_url to an Expo Router path.
 *
 * - Known routes → resolved=true, mapped path
 * - Unknown routes → resolved=false, DEFAULT_ROUTE
 * - Empty/malformed → resolved=false, DEFAULT_ROUTE + warning log
 */
export function resolveDeepLink(actionUrl: string): DeepLinkResult {
  if (!actionUrl || actionUrl.trim().length === 0) {
    console.warn("[DeepLink] Empty action_url received");
    return { resolved: false, route: DEFAULT_ROUTE, originalUrl: actionUrl };
  }

  // Normalize: strip trailing slash, lowercase
  const normalized = actionUrl.trim().replace(/\/+$/, "").toLowerCase();

  const mappedRoute = DEEP_LINK_ROUTES[normalized];

  if (mappedRoute) {
    return { resolved: true, route: mappedRoute, originalUrl: actionUrl };
  }

  console.warn(`[DeepLink] Unrecognized route: "${actionUrl}"`);
  return { resolved: false, route: DEFAULT_ROUTE, originalUrl: actionUrl };
}

/**
 * Type guard: check if an action_url maps to a known route.
 */
export function isValidDeepLink(actionUrl: string): boolean {
  if (!actionUrl || actionUrl.trim().length === 0) {
    return false;
  }
  const normalized = actionUrl.trim().replace(/\/+$/, "").toLowerCase();
  return normalized in DEEP_LINK_ROUTES;
}
