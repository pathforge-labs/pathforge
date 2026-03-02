/**
 * PathForge — Sentry Server Configuration
 * ==========================================
 * Sprint 35: Server-side error monitoring for Next.js API routes and SSR.
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "development",
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,

  // Performance sampling — match client config
  tracesSampleRate: 0.1,

  // PII scrubbing — strip auth headers
  beforeSend(event) {
    if (event.request?.headers) {
      delete event.request.headers["authorization"];
      delete event.request.headers["cookie"];
    }
    return event;
  },

  enabled: process.env.NODE_ENV === "production",
});
