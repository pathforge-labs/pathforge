/**
 * PathForge — Sentry Edge Configuration
 * ========================================
 * Sprint 35: Edge runtime error monitoring (middleware, edge API routes).
 * Sprint 36 WS-3: Production activation with noise filtering (Audit F8).
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "development",
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE ?? "unknown",

  tracesSampleRate: 0.1,

  // Sprint 36 WS-3: Noise filtering — mirror client/server
  ignoreErrors: [
    "ResizeObserver loop",
    "ChunkLoadError",
    "Loading chunk",
    "Network request failed",
    "AbortError",
  ],

  // Sprint 36 WS-3: Breadcrumb limits
  maxBreadcrumbs: 50,

  enabled: process.env.NODE_ENV === "production",
});
