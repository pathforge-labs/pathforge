"use client";

/**
 * PathForge — Skill Impact Chart
 * =================================
 * Horizontal bar chart of per-skill salary impact (positive/negative).
 * Sorted by magnitude, color-coded by direction.
 */

import type { SkillSalaryImpactResponse } from "@/types/api";

// ── Types ──────────────────────────────────────────────────

interface SkillImpactChartProps {
  /** Array of skill salary impact data */
  readonly impacts: SkillSalaryImpactResponse[];
  /** Currency code for formatting */
  readonly currency?: string;
  /** Maximum number of skills to show */
  readonly maxVisible?: number;
}

// ── Helpers ─────────────────────────────────────────────────

function formatAmount(amount: number, currency: string): string {
  const prefix = amount >= 0 ? "+" : "";
  return `${prefix}${new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount)}`;
}

// ── Component ───────────────────────────────────────────────

export function SkillImpactChart({
  impacts,
  currency = "EUR",
  maxVisible = 10,
}: SkillImpactChartProps): React.JSX.Element {
  const sorted = [...impacts]
    .sort((a, b) => Math.abs(b.salary_impact_amount) - Math.abs(a.salary_impact_amount))
    .slice(0, maxVisible);

  if (sorted.length === 0) {
    return (
      <div className="skill-impact-chart skill-impact-chart--empty">
        <p>No skill impact data available.</p>
      </div>
    );
  }

  const maxImpact = Math.max(...sorted.map((s) => Math.abs(s.salary_impact_amount)), 1);

  return (
    <div className="skill-impact-chart" role="list" aria-label="Skill salary impact">
      {sorted.map((impact) => {
        const widthPercent = (Math.abs(impact.salary_impact_amount) / maxImpact) * 100;
        const isPositive = impact.impact_direction === "positive";

        return (
          <div
            key={impact.id}
            className="skill-impact-chart__item"
            role="listitem"
            aria-label={`${impact.skill_name}: ${formatAmount(impact.salary_impact_amount, currency)}`}
          >
            <div className="skill-impact-chart__label">
              <span className="skill-impact-chart__skill-name">{impact.skill_name}</span>
              <span className="skill-impact-chart__category">{impact.category}</span>
            </div>
            <div className="skill-impact-chart__bar-container">
              <div
                className={`skill-impact-chart__bar skill-impact-chart__bar--${isPositive ? "positive" : "negative"}`}
                style={{ width: `${widthPercent}%` }}
                role="progressbar"
                aria-valuenow={Math.round(Math.abs(impact.salary_impact_amount))}
                aria-valuemin={0}
                aria-valuemax={Math.round(maxImpact)}
              />
            </div>
            <div className="skill-impact-chart__value">
              <span className={`skill-impact-chart__amount skill-impact-chart__amount--${isPositive ? "positive" : "negative"}`}>
                {formatAmount(impact.salary_impact_amount, currency)}
              </span>
              <span className="skill-impact-chart__percent">
                ({impact.salary_impact_percent > 0 ? "+" : ""}{impact.salary_impact_percent.toFixed(1)}%)
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}
