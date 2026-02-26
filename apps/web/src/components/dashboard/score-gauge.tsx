/**
 * PathForge — Score Gauge
 * ========================
 * Reusable SVG semicircular gauge for 0–100 scores.
 * Used for: Career Moat Score, Automation Risk, Protection Score.
 */

"use client";

/* ── Types ────────────────────────────────────────────────── */

export interface ScoreGaugeProps {
  /** Numeric score (0–100) */
  readonly score: number;
  /** Primary label text */
  readonly label: string;
  /** Maximum possible score */
  readonly maxScore?: number;
  /** Whether the gauge is loading */
  readonly isLoading?: boolean;
  /** Optional subtitle below score */
  readonly subtitle?: string;
}

/* ── Constants ────────────────────────────────────────────── */

const RADIUS = 60;
const STROKE_WIDTH = 10;
const CIRCUMFERENCE = Math.PI * RADIUS;
const CENTER_X = 80;
const CENTER_Y = 75;

/* ── Helpers ──────────────────────────────────────────────── */

function getScoreColor(score: number): string {
  if (score >= 80) return "hsl(142 71% 45%)";
  if (score >= 60) return "hsl(48 96% 53%)";
  if (score >= 40) return "hsl(25 95% 53%)";
  return "hsl(0 84% 60%)";
}

function getScoreTextColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
}

function getScoreLabel(score: number): string {
  if (score >= 80) return "Strong";
  if (score >= 60) return "Moderate";
  if (score >= 40) return "Developing";
  return "Vulnerable";
}

/* ── Component ────────────────────────────────────────────── */

export function ScoreGauge({
  score,
  label,
  maxScore = 100,
  isLoading = false,
  subtitle,
}: ScoreGaugeProps) {
  const normalizedScore = Math.max(0, Math.min(maxScore, score));
  const percentage = (normalizedScore / maxScore) * 100;
  const offset = CIRCUMFERENCE - (percentage / 100) * CIRCUMFERENCE;

  return (
    <div className="flex flex-col items-center gap-1">
      <svg
        viewBox="0 0 160 90"
        className="w-full max-w-[180px]"
        role="img"
        aria-label={`${label}: ${normalizedScore} out of ${maxScore}`}
      >
        {/* Background arc */}
        <path
          d={`M ${CENTER_X - RADIUS} ${CENTER_Y} A ${RADIUS} ${RADIUS} 0 0 1 ${CENTER_X + RADIUS} ${CENTER_Y}`}
          fill="none"
          stroke="currentColor"
          strokeWidth={STROKE_WIDTH}
          strokeLinecap="round"
          className="text-muted/20"
        />

        {/* Score arc */}
        {!isLoading && (
          <path
            d={`M ${CENTER_X - RADIUS} ${CENTER_Y} A ${RADIUS} ${RADIUS} 0 0 1 ${CENTER_X + RADIUS} ${CENTER_Y}`}
            fill="none"
            stroke={getScoreColor(percentage)}
            strokeWidth={STROKE_WIDTH}
            strokeLinecap="round"
            strokeDasharray={CIRCUMFERENCE}
            strokeDashoffset={offset}
            className="transition-all duration-1000 ease-out"
          />
        )}

        {/* Center score text */}
        <text
          x={CENTER_X}
          y={CENTER_Y - 12}
          textAnchor="middle"
          className={`fill-current ${isLoading ? "text-muted-foreground animate-pulse" : getScoreTextColor(percentage)}`}
          fontSize="28"
          fontWeight="700"
        >
          {isLoading ? "···" : normalizedScore}
        </text>

        {/* Score label */}
        <text
          x={CENTER_X}
          y={CENTER_Y + 2}
          textAnchor="middle"
          className="fill-current text-muted-foreground"
          fontSize="9"
          fontWeight="500"
          letterSpacing="0.05em"
        >
          {isLoading ? "Loading" : getScoreLabel(percentage)}
        </text>
      </svg>

      {/* Label below gauge */}
      <p className="text-center text-sm font-medium text-foreground">{label}</p>
      {subtitle && (
        <p className="text-center text-xs text-muted-foreground">{subtitle}</p>
      )}
    </div>
  );
}
