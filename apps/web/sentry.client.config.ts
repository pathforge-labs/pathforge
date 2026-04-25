/**
 * PathForge — Sentry Client Configuration
 * ==========================================
 * Sprint 35: Browser-side error monitoring.
 * Sprint 36 WS-3: Production activation with noise filtering.
 *
 * Mirrors backend Sentry config (`apps/api/app/core/sentry.py`):
 * - PII denylist maintained
 * - Conservative sampling (10% traces)
 * - No session replay (privacy)
 * - ignoreErrors + denyUrls for noise reduction
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "development",
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE ?? "unknown",

  // Performance sampling — conservative start, ramp in production
  tracesSampleRate: 0.1,

  // Session replay — disabled for privacy
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,

  // Sprint 36 WS-3: Noise filtering (Audit F9)
  ignoreErrors: [
    "ResizeObserver loop",
    "ChunkLoadError",
    "Loading chunk",
    "Network request failed",
    "AbortError",
  ],
  denyUrls: [
    /extensions\//i,
    /^chrome:\/\//i,
    /^moz-extension:\/\//i,
  ],

  // Sprint 36 WS-3: Breadcrumb limits (Audit F2)
  maxBreadcrumbs: 50,

  // PII scrubbing — strip sensitive fields before sending
  beforeSend(event) {
    if (event.request?.headers) {
      delete event.request.headers["Authorization"];
      delete event.request.headers["Cookie"];
      delete event.request.headers["Set-Cookie"];
    }
    return event;
  },

  // Don't send events in development
  enabled: process.env.NODE_ENV === "production",
});
