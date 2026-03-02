/**
 * PathForge — Sentry Edge Configuration
 * ========================================
 * Sprint 35: Edge runtime error monitoring (middleware, edge API routes).
 */

import * as Sentry from "@sentry/nextjs";

Sentry.init({
  dsn: process.env.NEXT_PUBLIC_SENTRY_DSN,
  environment: process.env.NEXT_PUBLIC_SENTRY_ENVIRONMENT ?? "development",
  release: process.env.NEXT_PUBLIC_SENTRY_RELEASE,

  tracesSampleRate: 0.1,

  enabled: process.env.NODE_ENV === "production",
});
