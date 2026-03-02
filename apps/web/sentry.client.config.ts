/**
 * PathForge — Sentry Client Configuration
 * ==========================================
 * Sprint 35: Browser-side error monitoring.
 *
 * Mirrors backend Sentry config (`apps/api/app/core/sentry.py`):
 * - PII denylist maintained
 * - Conservative sampling (10% traces)
 * - No session replay (privacy)
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "development",
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,

  // Performance sampling — conservative start, ramp in production
  tracesSampleRate: 0.1,

  // Session replay — disabled for privacy
  replaysSessionSampleRate: 0,
  replaysOnErrorSampleRate: 0,

  // PII scrubbing — strip sensitive fields before sending
  beforeSend(event) {
    if (event.request?.headers) {
      delete event.request.headers["Authorization"];
      delete event.request.headers["Cookie"];
    }
    return event;
  },

  // Don't send events in development
  enabled: process.env.NODE_ENV === "production",
});
