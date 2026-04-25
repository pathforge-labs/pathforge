"use client";

/**
 * PathForge — Freshness Indicator
 * ==================================
 * Horizontal bar chart per skill showing freshness score (0–100).
 * Color coding: green (≥80), gold (≥60), orange (≥40), red (<40).
 */

import type { SkillFreshnessResponse } from "@/types/api";

// ── Types ──────────────────────────────────────────────────

interface FreshnessIndicatorProps {
  /** Array of skill freshness data */
  readonly skills: SkillFreshnessResponse[];
  /** Maximum number of skills to show */
  readonly maxVisible?: number;
}

// ── Helpers ─────────────────────────────────────────────────

function getFreshnessColor(score: number): string {
  if (score >= 80) return "var(--color-success, #22c55e)";
  if (score >= 60) return "var(--color-warning-light, #eab308)";
  if (score >= 40) return "var(--color-warning, #f97316)";
  return "var(--color-danger, #ef4444)";
}

function getUrgencyLabel(urgency: number): string {
  if (urgency >= 0.8) return "Critical";
  if (urgency >= 0.6) return "High";
  if (urgency >= 0.4) return "Medium";
  return "Low";
}

// ── Component ───────────────────────────────────────────────

export function FreshnessIndicator({
  skills,
  maxVisible = 10,
}: FreshnessIndicatorProps): React.JSX.Element {
  const sortedSkills = [...skills]
    .sort((a, b) => a.freshness_score - b.freshness_score)
    .slice(0, maxVisible);

  if (sortedSkills.length === 0) {
    return (
      <div className="freshness-indicator freshness-indicator--empty">
        <p>No skill freshness data available.</p>
      </div>
    );
  }

  return (
    <div className="freshness-indicator" role="list" aria-label="Skill freshness scores">
      {sortedSkills.map((skill) => (
        <div
          key={skill.id}
          className="freshness-indicator__item"
          role="listitem"
          aria-label={`${skill.skill_name}: ${Math.round(skill.freshness_score)}% fresh`}
        >
          <div className="freshness-indicator__label">
            <span className="freshness-indicator__skill-name">{skill.skill_name}</span>
            <span className="freshness-indicator__category">{skill.category}</span>
          </div>
          <div className="freshness-indicator__bar-container">
            <div
              className="freshness-indicator__bar"
              style={{
                width: `${skill.freshness_score}%`,
                backgroundColor: getFreshnessColor(skill.freshness_score),
              }}
              role="progressbar"
              aria-valuenow={Math.round(skill.freshness_score)}
              aria-valuemin={0}
              aria-valuemax={100}
            />
          </div>
          <div className="freshness-indicator__meta">
            <span className="freshness-indicator__score">
              {Math.round(skill.freshness_score)}%
            </span>
            <span
              className={`freshness-indicator__urgency freshness-indicator__urgency--${getUrgencyLabel(skill.refresh_urgency).toLowerCase()}`}
            >
              {getUrgencyLabel(skill.refresh_urgency)}
            </span>
          </div>
        </div>
      ))}
    </div>
  );
}
