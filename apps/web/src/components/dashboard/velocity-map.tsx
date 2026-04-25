"use client";

/**
 * PathForge — Velocity Map
 * ==========================
 * Skill velocity cards showing direction, composite health, and component split.
 */

import type { SkillVelocityEntryResponse } from "@/types/api";

// ── Types ──────────────────────────────────────────────────

interface VelocityMapProps {
  /** Array of skill velocity data */
  readonly velocities: SkillVelocityEntryResponse[];
  /** Maximum number of cards to show */
  readonly maxVisible?: number;
}

// ── Helpers ─────────────────────────────────────────────────

function getDirectionArrow(direction: string): string {
  switch (direction.toLowerCase()) {
    case "accelerating": return "↑";
    case "stable": return "→";
    case "decelerating": return "↓";
    default: return "•";
  }
}

function getDirectionColor(direction: string): string {
  switch (direction.toLowerCase()) {
    case "accelerating": return "var(--color-success, #22c55e)";
    case "stable": return "var(--color-info, #3b82f6)";
    case "decelerating": return "var(--color-danger, #ef4444)";
    default: return "var(--color-muted, #6b7280)";
  }
}

function getHealthLabel(health: number): string {
  if (health >= 80) return "Excellent";
  if (health >= 60) return "Good";
  if (health >= 40) return "Fair";
  return "Poor";
}

// ── Component ───────────────────────────────────────────────

export function VelocityMap({
  velocities,
  maxVisible = 12,
}: VelocityMapProps): React.JSX.Element {
  const sorted = [...velocities]
    .sort((a, b) => b.velocity_score - a.velocity_score)
    .slice(0, maxVisible);

  if (sorted.length === 0) {
    return (
      <div className="velocity-map velocity-map--empty">
        <p>No velocity data available.</p>
      </div>
    );
  }

  return (
    <div className="velocity-map" role="list" aria-label="Skill velocity map">
      {sorted.map((entry) => (
        <div
          key={entry.id}
          className="velocity-map__card"
          role="listitem"
          aria-label={`${entry.skill_name}: ${entry.velocity_direction}`}
        >
          <div className="velocity-map__header">
            <span className="velocity-map__skill-name">{entry.skill_name}</span>
            <span
              className="velocity-map__direction"
              style={{ color: getDirectionColor(entry.velocity_direction) }}
              aria-label={entry.velocity_direction}
            >
              {getDirectionArrow(entry.velocity_direction)}
            </span>
          </div>

          {/* Composite Health Bar */}
          <div className="velocity-map__health">
            <div className="velocity-map__health-bar-container">
              <div
                className="velocity-map__health-bar"
                style={{ width: `${entry.composite_health}%` }}
                role="progressbar"
                aria-valuenow={Math.round(entry.composite_health)}
                aria-valuemin={0}
                aria-valuemax={100}
                aria-label="Composite health"
              />
            </div>
            <span className="velocity-map__health-label">
              {getHealthLabel(entry.composite_health)}
            </span>
          </div>

          {/* Velocity Score */}
          <div className="velocity-map__score">
            <span className="velocity-map__score-value">
              {entry.velocity_score > 0 ? "+" : ""}{Math.round(entry.velocity_score)}
            </span>
            <span className="velocity-map__score-unit">velocity</span>
          </div>

          {/* Freshness vs Demand Split */}
          {entry.freshness_component != null && entry.demand_component != null && (
            <div className="velocity-map__split" aria-label="Freshness vs demand components">
              <div className="velocity-map__split-bar">
                <div
                  className="velocity-map__split-freshness"
                  style={{ width: `${Math.max(0, Math.min(100, entry.freshness_component))}%` }}
                  title={`Freshness: ${Math.round(entry.freshness_component)}%`}
                />
                <div
                  className="velocity-map__split-demand"
                  style={{ width: `${Math.max(0, Math.min(100, entry.demand_component))}%` }}
                  title={`Demand: ${Math.round(entry.demand_component)}%`}
                />
              </div>
              <div className="velocity-map__split-labels">
                <span>Freshness</span>
                <span>Demand</span>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
