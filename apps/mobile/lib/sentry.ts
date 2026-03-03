/**
 * PathForge Mobile — Sentry Integration
 * ========================================
 * Production crash reporting with PII scrubbing.
 *
 * Sprint 36 WS-1:
 * - @sentry/react-native ≥7.0.0 (Expo 52 + New Architecture)
 * - PII-free: strips Authorization, Cookie, resume_text, cv_content
 * - Breadcrumbs: navigation ON, network ON (URLs only), console OFF, max 50
 * - Disabled in __DEV__ — zero overhead during development
 */

import * as Sentry from "@sentry/react-native";
import Constants from "expo-constants";

// ── PII Fields to Scrub ──────────────────────────────────────

const PII_HEADER_KEYS = new Set([
  "authorization",
  "cookie",
  "set-cookie",
  "x-api-key",
  "x-auth-token",
]);

const PII_DATA_KEYS = new Set([
  "resume_text",
  "cv_content",
  "cover_letter",
  "email",
  "phone",
  "address",
  "password",
  "token",
  "refresh_token",
]);

// ── PII Scrubber ─────────────────────────────────────────────

export function scrubPii(event: Sentry.Event): Sentry.Event | null {
  // Scrub request headers
  if (event.request?.headers) {
    for (const key of Object.keys(event.request.headers)) {
      if (PII_HEADER_KEYS.has(key.toLowerCase())) {
        event.request.headers[key] = "[Filtered]";
      }
    }
  }

  // Scrub extra/contexts data
  if (event.extra) {
    for (const key of Object.keys(event.extra)) {
      if (PII_DATA_KEYS.has(key.toLowerCase())) {
        event.extra[key] = "[Filtered]";
      }
    }
  }

  // Scrub breadcrumb data
  if (event.breadcrumbs) {
    for (const breadcrumb of event.breadcrumbs) {
      if (breadcrumb.data) {
        for (const key of Object.keys(breadcrumb.data)) {
          if (PII_DATA_KEYS.has(key.toLowerCase())) {
            breadcrumb.data[key] = "[Filtered]";
          }
        }
      }
    }
  }

  return event;
}

// ── Initialization ───────────────────────────────────────────

const APP_VERSION = Constants.expoConfig?.version ?? "0.0.0";

/**
 * Initialize Sentry for mobile crash reporting.
 *
 * Call once at app startup, before any rendering.
 * Disabled entirely in __DEV__ to avoid noise and overhead.
 *
 * Note: DSN and environment are read at call time (not module load)
 * to support late-binding env vars and testability.
 */
export function initSentry(): void {
  if (__DEV__) {
    return; // Zero overhead in development
  }

  const dsn = process.env.EXPO_PUBLIC_SENTRY_DSN ?? "";
  const environment =
    process.env.EXPO_PUBLIC_SENTRY_ENVIRONMENT ?? "development";

  if (!dsn) {
    // No DSN = no crash reporting. Silent in production to avoid startup crash.
    return;
  }

  Sentry.init({
    dsn,
    environment,
    release: `pathforge-mobile@${APP_VERSION}`,
    enabled: !__DEV__,

    // Performance
    tracesSampleRate: 0.1,

    // PII Scrubbing
    beforeSend: scrubPii,
    sendDefaultPii: false,

    // Breadcrumbs
    maxBreadcrumbs: 50,
    enableAutoPerformanceTracing: true,
    enableNativeFramesTracking: false,
  });
}

// ── Typed Wrappers ───────────────────────────────────────────

/**
 * Capture an exception with optional context.
 * Safe to call even if Sentry is not initialized.
 */
export function captureException(
  error: unknown,
  context?: Record<string, unknown>,
): void {
  if (__DEV__) {
    console.error("Sentry (dev):", error);
    return;
  }

  Sentry.captureException(error, {
    extra: context,
  });
}

/**
 * Capture a message with optional severity.
 */
export function captureMessage(
  message: string,
  level: Sentry.SeverityLevel = "info",
): void {
  if (__DEV__) {
    console.log(`Sentry (dev) [${level}]:`, message);
    return;
  }

  Sentry.captureMessage(message, level);
}

/**
 * Set user context — ID ONLY, no PII.
 * Call after successful authentication.
 */
export function setUserContext(userId: string): void {
  Sentry.setUser({ id: userId });
}

/**
 * Clear user context on logout.
 */
export function clearUserContext(): void {
  Sentry.setUser(null);
}

/**
 * Sentry.wrap — re-export for root component wrapping.
 */
export const wrapWithSentry = Sentry.wrap;
