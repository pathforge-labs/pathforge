"use client";

/**
 * PathForge — Transition Card
 * ==============================
 * Card for a career transition path.
 * Shows: from → to role, difficulty badge, skill overlap bar, success probability.
 */

import type { TransitionSummaryResponse } from "@/types/api";

// ── Types ──────────────────────────────────────────────────

interface TransitionCardProps {
  /** Transition summary data */
  readonly transition: TransitionSummaryResponse;
  /** Click handler for navigation to detail view */
  readonly onClick?: (transitionId: string) => void;
  /** Delete handler */
  readonly onDelete?: (transitionId: string) => void;
}

// ── Helpers ─────────────────────────────────────────────────

function getDifficultyColor(difficulty: string): string {
  switch (difficulty.toLowerCase()) {
    case "easy": return "var(--color-success, #22c55e)";
    case "moderate": return "var(--color-warning-light, #eab308)";
    case "hard": return "var(--color-warning, #f97316)";
    case "very_hard": return "var(--color-danger, #ef4444)";
    default: return "var(--color-muted, #6b7280)";
  }
}

function getDifficultyLabel(difficulty: string): string {
  const labels: Record<string, string> = {
    easy: "Easy",
    moderate: "Moderate",
    hard: "Hard",
    very_hard: "Very Hard",
  };
  return labels[difficulty.toLowerCase()] ?? difficulty;
}

function getConfidenceColor(score: number): string {
  if (score >= 0.7) return "var(--color-success, #22c55e)";
  if (score >= 0.5) return "var(--color-warning-light, #eab308)";
  return "var(--color-danger, #ef4444)";
}

function formatDate(isoString: string): string {
  return new Date(isoString).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// ── Component ───────────────────────────────────────────────

export function TransitionCard({
  transition,
  onClick,
  onDelete,
}: TransitionCardProps): React.JSX.Element {
  return (
    <article
      className="transition-card"
      aria-label={`Transition from ${transition.from_role} to ${transition.to_role}`}
      onClick={() => onClick?.(transition.id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onClick?.(transition.id);
        }
      }}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Role Path */}
      <div className="transition-card__path">
        <span className="transition-card__from-role">{transition.from_role}</span>
        <span className="transition-card__arrow" aria-hidden="true">→</span>
        <span className="transition-card__to-role">{transition.to_role}</span>
      </div>

      {/* Difficulty Badge */}
      <span
        className="transition-card__difficulty"
        style={{ color: getDifficultyColor(transition.difficulty) }}
      >
        {getDifficultyLabel(transition.difficulty)}
      </span>

      {/* Skill Overlap Bar */}
      <div className="transition-card__overlap-section">
        <div className="transition-card__overlap-header">
          <span className="transition-card__overlap-label">Skill Overlap</span>
          <span className="transition-card__overlap-value">
            {Math.round(transition.skill_overlap_percent)}%
          </span>
        </div>
        <div className="transition-card__overlap-bar-container">
          <div
            className="transition-card__overlap-bar"
            style={{ width: `${transition.skill_overlap_percent}%` }}
            role="progressbar"
            aria-valuenow={Math.round(transition.skill_overlap_percent)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label="Skill overlap percentage"
          />
        </div>
      </div>

      {/* Metrics Row */}
      <div className="transition-card__metrics">
        <div className="transition-card__metric">
          <span className="transition-card__metric-label">Confidence</span>
          <span
            className="transition-card__metric-value"
            style={{ color: getConfidenceColor(transition.confidence_score) }}
          >
            {Math.round(transition.confidence_score * 100)}%
          </span>
        </div>

        {transition.estimated_duration_months != null && (
          <div className="transition-card__metric">
            <span className="transition-card__metric-label">Timeline</span>
            <span className="transition-card__metric-value">
              {transition.estimated_duration_months} mo
            </span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="transition-card__footer">
        <span className="transition-card__date">{formatDate(transition.computed_at)}</span>
        {onDelete && (
          <button
            className="transition-card__delete"
            onClick={(event) => {
              event.stopPropagation();
              onDelete(transition.id);
            }}
            aria-label="Delete transition"
            type="button"
          >
            ✕
          </button>
        )}
      </div>
    </article>
  );
}
