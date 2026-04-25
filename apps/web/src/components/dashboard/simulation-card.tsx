"use client";

/**
 * PathForge — Simulation Card
 * ==============================
 * Card component for a career simulation scenario.
 * Shows: scenario type badge, confidence, ROI, salary impact, timeline.
 */

import type { SimulationSummaryResponse } from "@/types/api";

// ── Types ──────────────────────────────────────────────────

interface SimulationCardProps {
  /** Simulation summary data */
  readonly simulation: SimulationSummaryResponse;
  /** Click handler for navigation to detail view */
  readonly onClick?: (simulationId: string) => void;
  /** Delete handler */
  readonly onDelete?: (simulationId: string) => void;
}

// ── Helpers ─────────────────────────────────────────────────

function getScenarioLabel(type: string): string {
  const labels: Record<string, string> = {
    role_transition: "Role Change",
    geo_move: "Relocation",
    skill_investment: "Skill Investment",
    industry_pivot: "Industry Pivot",
    seniority_jump: "Seniority Jump",
  };
  return labels[type] ?? type.replace(/_/g, " ");
}

function getScenarioEmoji(type: string): string {
  const emojis: Record<string, string> = {
    role_transition: "🎯",
    geo_move: "🌍",
    skill_investment: "📚",
    industry_pivot: "🔄",
    seniority_jump: "📈",
  };
  return emojis[type] ?? "🔮";
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

export function SimulationCard({
  simulation,
  onClick,
  onDelete,
}: SimulationCardProps): React.JSX.Element {
  return (
    <article
      className="simulation-card"
      aria-label={`${getScenarioLabel(simulation.scenario_type)} simulation`}
      onClick={() => onClick?.(simulation.id)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          onClick?.(simulation.id);
        }
      }}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      {/* Header */}
      <div className="simulation-card__header">
        <span className="simulation-card__emoji" aria-hidden="true">
          {getScenarioEmoji(simulation.scenario_type)}
        </span>
        <span className="simulation-card__type-badge">
          {getScenarioLabel(simulation.scenario_type)}
        </span>
        <span className={`simulation-card__status simulation-card__status--${simulation.status}`}>
          {simulation.status}
        </span>
      </div>

      {/* Metrics */}
      <div className="simulation-card__metrics">
        <div className="simulation-card__metric">
          <span className="simulation-card__metric-label">Confidence</span>
          <span
            className="simulation-card__metric-value"
            style={{ color: getConfidenceColor(simulation.confidence_score) }}
          >
            {Math.round(simulation.confidence_score * 100)}%
          </span>
        </div>

        {simulation.salary_impact_percent != null && (
          <div className="simulation-card__metric">
            <span className="simulation-card__metric-label">Salary Impact</span>
            <span className={`simulation-card__metric-value simulation-card__metric-value--${simulation.salary_impact_percent >= 0 ? "positive" : "negative"}`}>
              {simulation.salary_impact_percent >= 0 ? "+" : ""}{simulation.salary_impact_percent.toFixed(1)}%
            </span>
          </div>
        )}

        {simulation.estimated_months != null && (
          <div className="simulation-card__metric">
            <span className="simulation-card__metric-label">Timeline</span>
            <span className="simulation-card__metric-value">
              {simulation.estimated_months} mo
            </span>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="simulation-card__footer">
        <span className="simulation-card__date">{formatDate(simulation.computed_at)}</span>
        {onDelete && (
          <button
            className="simulation-card__delete"
            onClick={(event) => {
              event.stopPropagation();
              onDelete(simulation.id);
            }}
            aria-label="Delete simulation"
            type="button"
          >
            ✕
          </button>
        )}
      </div>
    </article>
  );
}
