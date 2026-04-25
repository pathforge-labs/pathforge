/**
 * PathForge — Sentry Server Configuration
 * ==========================================
 * Sprint 35: Server-side error monitoring for Next.js API routes and SSR.
 * Sprint 36 WS-3: Production activation with noise filtering.
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "development",
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE ?? "unknown",

  // Performance sampling — match client config
  tracesSampleRate: 0.1,

  // Sprint 36 WS-3: Noise filtering — mirror client
  ignoreErrors: [
    "ResizeObserver loop",
    "ChunkLoadError",
    "Loading chunk",
    "Network request failed",
    "AbortError",
  ],

  // Sprint 36 WS-3: Breadcrumb limits
  maxBreadcrumbs: 50,

  // PII scrubbing — strip auth headers
  beforeSend(event) {
    if (event.request?.headers) {
      delete event.request.headers["authorization"];
      delete event.request.headers["cookie"];
      delete event.request.headers["set-cookie"];
    }
    return event;
  },

  enabled: process.env.NODE_ENV === "production",
});
