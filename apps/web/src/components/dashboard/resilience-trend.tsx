/**
 * PathForge — Career Resilience Score™ Trend Chart
 * ===================================================
 * Sprint 36 WS-5: Time-series visualization of resilience score.
 *
 * Key decisions:
 * - next/dynamic({ ssr: false }) — avoids Recharts hydration mismatch (F14)
 * - ResponsiveContainer — prevents layout shift
 * - Gradient fill — premium visual
 * - Skeleton loading — smooth UX
 */

"use client";

import dynamic from "next/dynamic";
import { useState, type JSX } from "react";
import { useResilienceTrend, type ResilienceDataPoint } from "@/hooks/api/use-resilience-trend";
import styles from "./resilience-trend.module.css";

// ── Dynamic Import (SSR: false) ──────────────────────────────

const RechartsChart = dynamic(() => import("./resilience-trend-chart"), {
  ssr: false,
  loading: () => <ChartSkeleton />,
});

// ── Time Range Selector ──────────────────────────────────────

type TimeRange = 30 | 90 | 365;

const TIME_RANGES: readonly { readonly value: TimeRange; readonly label: string }[] = [
  { value: 30, label: "30d" },
  { value: 90, label: "90d" },
  { value: 365, label: "1y" },
] as const;

// ── Skeleton Loader ──────────────────────────────────────────

function ChartSkeleton(): JSX.Element {
  return (
    <div className={styles.skeleton}>
      <div className={styles.skeletonBar} />
      <div className={styles.skeletonBar} style={{ height: "60%" }} />
      <div className={styles.skeletonBar} style={{ height: "75%" }} />
      <div className={styles.skeletonBar} style={{ height: "45%" }} />
      <div className={styles.skeletonBar} style={{ height: "85%" }} />
    </div>
  );
}

// ── Empty State ──────────────────────────────────────────────

function EmptyState(): JSX.Element {
  return (
    <div className={styles.emptyState}>
      <p className={styles.emptyText}>
        Not enough data yet. Your resilience trend will appear after at least 2 assessments.
      </p>
    </div>
  );
}

// ── Main Component ───────────────────────────────────────────

export function ResilienceTrend(): JSX.Element {
  const [days, setDays] = useState<TimeRange>(90);
  const { data, isLoading, isError } = useResilienceTrend(days);

  return (
    <section className={styles.container} aria-label="Career Resilience Score Trend">
      <header className={styles.header}>
        <h3 className={styles.title}>Resilience Trend</h3>
        <div className={styles.rangeSelector} role="radiogroup" aria-label="Time range">
          {TIME_RANGES.map(({ value, label }) => (
            <button
              key={value}
              className={`${styles.rangeButton} ${days === value ? styles.rangeActive : ""}`}
              onClick={() => setDays(value)}
              aria-pressed={days === value}
              type="button"
            >
              {label}
            </button>
          ))}
        </div>
      </header>

      <div className={styles.chartWrapper}>
        {isLoading ? (
          <ChartSkeleton />
        ) : isError ? (
          <EmptyState />
        ) : !data?.data || data.data.length < 2 ? (
          <EmptyState />
        ) : (
          <RechartsChart data={data.data as ResilienceDataPoint[]} />
        )}
      </div>
    </section>
  );
}
