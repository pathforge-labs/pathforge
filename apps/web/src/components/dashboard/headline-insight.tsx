"use client";

/**
 * PathForge — Headline Insight
 * ===============================
 * Personalized insight callout that appears above charts.
 * Transforms data into a single decision-support sentence.
 */

import type { ReactNode } from "react";

// ── Types ──────────────────────────────────────────────────

interface HeadlineInsightProps {
  /** The insight icon (emoji) */
  readonly icon?: string;
  /** The primary insight message */
  readonly message: ReactNode;
  /** Optional secondary detail */
  readonly detail?: ReactNode;
  /** Visual variant */
  readonly variant?: "info" | "warning" | "success" | "neutral";
}

// ── Component ───────────────────────────────────────────────

export function HeadlineInsight({
  icon = "💡",
  message,
  detail,
  variant = "info",
}: HeadlineInsightProps): React.JSX.Element {
  return (
    <div
      className={`headline-insight headline-insight--${variant}`}
      role="status"
      aria-label="Personalized insight"
    >
      <span className="headline-insight__icon" aria-hidden="true">{icon}</span>
      <div className="headline-insight__content">
        <p className="headline-insight__message">{message}</p>
        {detail && (
          <p className="headline-insight__detail">{detail}</p>
        )}
      </div>
    </div>
  );
}
