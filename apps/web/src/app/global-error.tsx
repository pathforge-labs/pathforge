/**
 * PathForge — Global Error Boundary
 * ====================================
 * Sprint 35 (FA1): Next.js App Router global error handler.
 *
 * Captures unhandled errors and reports them to Sentry.
 * Provides a user-friendly fallback UI.
 *
 * @see https://nextjs.org/docs/app/building-your-application/routing/error-handling
 */

"use client";

import * as Sentry from "@sentry/nextjs";
import { useEffect } from "react";

import { APP_NAME } from "@/config/brand";

interface GlobalErrorProps {
  readonly error: Error & { digest?: string };
  readonly reset: () => void;
}

export default function GlobalError({ error, reset }: GlobalErrorProps) {
  useEffect(() => {
    Sentry.captureException(error);
  }, [error]);

  return (
    <html lang="en">
      <body>
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "100vh",
            fontFamily: "'Inter', system-ui, sans-serif",
            textAlign: "center",
            padding: "2rem",
            background: "#0a0a0a",
            color: "#fafafa",
          }}
        >
          <h1 style={{ fontSize: "1.5rem", marginBottom: "1rem" }}>
            Something went wrong
          </h1>
          <p style={{ color: "#888", marginBottom: "2rem", maxWidth: "40ch" }}>
            An unexpected error occurred. Our team has been notified and is
            looking into it.
          </p>
          <button
            type="button"
            onClick={reset}
            style={{
              padding: "0.75rem 1.5rem",
              borderRadius: "0.5rem",
              background: "#2563eb",
              color: "#fff",
              border: "none",
              cursor: "pointer",
              fontSize: "0.875rem",
              fontWeight: 500,
            }}
          >
            Try again
          </button>
          {/* eslint-disable-next-line @next/next/no-html-link-for-pages -- global-error renders outside App Router context, <Link> unavailable */}
          <a
            href="/"
            style={{
              marginTop: "1rem",
              color: "#666",
              fontSize: "0.8125rem",
              textDecoration: "underline",
            }}
          >
            Return to {APP_NAME}
          </a>
        </div>
      </body>
    </html>
  );
}
