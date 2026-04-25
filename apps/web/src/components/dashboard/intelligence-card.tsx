"use client";

/**
 * PathForge — Intelligence Card
 * ================================
 * Shared card wrapper for all Intelligence Hub modules.
 * Provides 5 named slots: headline, body, actions, connectedInsights, emptyState.
 */

import type { ReactNode } from "react";

// ── Types ──────────────────────────────────────────────────

interface IntelligenceCardProps {
  /** Card title displayed in the header */
  readonly title: string;
  /** Icon emoji or component for the header */
  readonly icon: string;
  /** Whether data is currently loading */
  readonly isLoading?: boolean;
  /** Whether there is scan data available */
  readonly hasData?: boolean;
  /** Last scan timestamp (ISO string) */
  readonly lastScanAt?: string | null;
  /** Headline insight — personalized sentence above body */
  readonly headline?: ReactNode;
  /** Main content area */
  readonly children: ReactNode;
  /** Action buttons (scan trigger, links, etc.) */
  readonly actions?: ReactNode;
  /** Cross-engine insight callouts */
  readonly connectedInsights?: ReactNode;
  /** Content to show when hasData is false */
  readonly emptyState?: ReactNode;
}

// ── Helpers ─────────────────────────────────────────────────

function formatScanTime(isoString: string): string {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMinutes = Math.floor(diffMs / 60_000);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMinutes < 1) return "Just now";
  if (diffMinutes < 60) return `${diffMinutes}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

// ── Skeleton ────────────────────────────────────────────────

function CardSkeleton(): React.JSX.Element {
  return (
    <div className="intelligence-card intelligence-card--loading" role="status" aria-label="Loading">
      <div className="intelligence-card__header">
        <div className="intelligence-card__skeleton intelligence-card__skeleton--title" />
      </div>
      <div className="intelligence-card__body">
        <div className="intelligence-card__skeleton intelligence-card__skeleton--line" />
        <div className="intelligence-card__skeleton intelligence-card__skeleton--line intelligence-card__skeleton--short" />
        <div className="intelligence-card__skeleton intelligence-card__skeleton--line intelligence-card__skeleton--medium" />
      </div>
    </div>
  );
}

// ── Component ───────────────────────────────────────────────

export function IntelligenceCard({
  title,
  icon,
  isLoading = false,
  hasData = true,
  lastScanAt,
  headline,
  children,
  actions,
  connectedInsights,
  emptyState,
}: IntelligenceCardProps): React.JSX.Element {
  if (isLoading) {
    return <CardSkeleton />;
  }

  return (
    <section className="intelligence-card" aria-label={title}>
      {/* ── Header ─────────────────────────────────────── */}
      <div className="intelligence-card__header">
        <div className="intelligence-card__title-group">
          <span className="intelligence-card__icon" aria-hidden="true">{icon}</span>
          <h2 className="intelligence-card__title">{title}</h2>
        </div>
        {lastScanAt && (
          <span className="intelligence-card__scan-time" title={new Date(lastScanAt).toLocaleString()}>
            Last scan: {formatScanTime(lastScanAt)}
          </span>
        )}
      </div>

      {/* ── Headline Insight ───────────────────────────── */}
      {headline && hasData && (
        <div className="intelligence-card__headline">
          {headline}
        </div>
      )}

      {/* ── Body (or Empty State) ──────────────────────── */}
      {hasData ? (
        <div className="intelligence-card__body">
          {children}
        </div>
      ) : (
        <div className="intelligence-card__empty">
          {emptyState ?? (
            <p className="intelligence-card__empty-text">
              No data yet. Run your first scan to get personalized intelligence.
            </p>
          )}
        </div>
      )}

      {/* ── Connected Insights ─────────────────────────── */}
      {connectedInsights && hasData && (
        <div className="intelligence-card__connected">
          {connectedInsights}
        </div>
      )}

      {/* ── Actions ────────────────────────────────────── */}
      {actions && (
        <div className="intelligence-card__actions">
          {actions}
        </div>
      )}
    </section>
  );
}
