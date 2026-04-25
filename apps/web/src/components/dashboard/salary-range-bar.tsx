"use client";

/**
 * PathForge — Salary Range Bar
 * ===============================
 * Horizontal min/median/max range bar with percentile indicator.
 */

import type { SalaryEstimateResponse } from "@/types/api";

// ── Types ──────────────────────────────────────────────────

interface SalaryRangeBarProps {
  /** Salary estimate data */
  readonly estimate: SalaryEstimateResponse;
}

// ── Helpers ─────────────────────────────────────────────────

function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function getConfidenceLabel(confidence: number): string {
  if (confidence >= 0.8) return "High";
  if (confidence >= 0.6) return "Moderate";
  return "Low";
}

// ── Component ───────────────────────────────────────────────

export function SalaryRangeBar({
  estimate,
}: SalaryRangeBarProps): React.JSX.Element {
  const range = estimate.estimated_max - estimate.estimated_min;
  const medianPosition = range > 0
    ? ((estimate.estimated_median - estimate.estimated_min) / range) * 100
    : 50;

  return (
    <div className="salary-range-bar" aria-label="Salary range estimate">
      {/* Role & Location Context */}
      <div className="salary-range-bar__context">
        <span className="salary-range-bar__role">{estimate.role_title}</span>
        <span className="salary-range-bar__location">{estimate.location}</span>
        <span className="salary-range-bar__seniority">{estimate.seniority_level}</span>
      </div>

      {/* Range Visualization */}
      <div className="salary-range-bar__visual">
        <div className="salary-range-bar__labels">
          <span className="salary-range-bar__min">
            {formatCurrency(estimate.estimated_min, estimate.currency)}
          </span>
          <span className="salary-range-bar__max">
            {formatCurrency(estimate.estimated_max, estimate.currency)}
          </span>
        </div>
        <div className="salary-range-bar__track">
          <div className="salary-range-bar__fill" />
          <div
            className="salary-range-bar__median-marker"
            style={{ left: `${medianPosition}%` }}
            aria-label={`Estimated median: ${formatCurrency(estimate.estimated_median, estimate.currency)}`}
          >
            <div className="salary-range-bar__median-dot" />
            <span className="salary-range-bar__median-label">
              {formatCurrency(estimate.estimated_median, estimate.currency)}
            </span>
          </div>
        </div>
      </div>

      {/* Confidence & Percentile */}
      <div className="salary-range-bar__meta">
        <span className="salary-range-bar__confidence">
          Confidence: {getConfidenceLabel(estimate.confidence)} ({Math.round(estimate.confidence * 100)}%)
        </span>
        {estimate.market_percentile != null && (
          <span className="salary-range-bar__percentile">
            Market percentile: {Math.round(estimate.market_percentile)}th
          </span>
        )}
      </div>

      {/* AI Transparency */}
      <p className="salary-range-bar__disclaimer">{estimate.disclaimer}</p>
    </div>
  );
}
