/**
 * PathForge — Instrumentation Hook
 * ===================================
 * Sprint 35: Next.js instrumentation for Sentry server-side initialization.
 *
 * @see https://nextjs.org/docs/app/building-your-application/optimizing/instrumentation
 */

export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME === "nodejs") {
    await import("../sentry.server.config");
  }

  if (process.env.NEXT_RUNTIME === "edge") {
    await import("../sentry.edge.config");
  }
}

export const onRequestError = async (): Promise<void> => {
  // Sentry captures errors automatically via the SDK
  // This hook is reserved for custom error processing if needed
};
