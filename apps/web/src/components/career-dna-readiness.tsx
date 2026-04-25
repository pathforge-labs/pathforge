/**
 * PathForge — Career DNA Readiness Score™
 * =========================================
 * Displays a composite readiness score with 6-dimension indicators.
 * Innovation: No competitor shows users how "ready" their career profile
 * is for intelligent career guidance.
 */

"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

/* ── Types ────────────────────────────────────────────────── */

interface DimensionStatus {
  readonly name: string;
  readonly icon: string;
  readonly completeness: "complete" | "partial" | "empty";
}

export interface CareerDnaReadinessProps {
  /** Overall readiness score (0–100) */
  readonly score: number;
  /** Individual dimension statuses */
  readonly dimensions: readonly DimensionStatus[];
  /** Whether the score is still loading */
  readonly isLoading?: boolean;
}

/* ── Constants ────────────────────────────────────────────── */

export const DEFAULT_DIMENSIONS: readonly DimensionStatus[] = [
  { name: "Skill Genome", icon: "🧬", completeness: "empty" },
  { name: "Experience Blueprint", icon: "📐", completeness: "empty" },
  { name: "Growth Vector", icon: "📈", completeness: "empty" },
  { name: "Values Profile", icon: "💎", completeness: "empty" },
  { name: "Market Position", icon: "🎯", completeness: "empty" },
  { name: "Career Resilience", icon: "🛡️", completeness: "empty" },
] as const;

/* ── Helpers ──────────────────────────────────────────────── */

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-500";
  if (score >= 60) return "text-yellow-500";
  if (score >= 40) return "text-orange-500";
  return "text-red-500";
}

function getScoreLabel(score: number): string {
  if (score >= 80) return "Excellent";
  if (score >= 60) return "Good";
  if (score >= 40) return "Fair";
  return "Getting Started";
}

function getScoreRingColor(score: number): string {
  if (score >= 80) return "stroke-green-500";
  if (score >= 60) return "stroke-yellow-500";
  if (score >= 40) return "stroke-orange-500";
  return "stroke-red-500";
}

function getCompletenessVariant(
  completeness: DimensionStatus["completeness"],
): "default" | "secondary" | "outline" {
  switch (completeness) {
    case "complete":
      return "default";
    case "partial":
      return "secondary";
    case "empty":
      return "outline";
  }
}

function getCompletenessLabel(completeness: DimensionStatus["completeness"]): string {
  switch (completeness) {
    case "complete":
      return "Complete";
    case "partial":
      return "Partial";
    case "empty":
      return "Pending";
  }
}

/* ── SVG Circular Progress ────────────────────────────────── */

const CIRCLE_RADIUS = 45;
const CIRCLE_CIRCUMFERENCE = 2 * Math.PI * CIRCLE_RADIUS;

function CircularScore({ score, isLoading }: { readonly score: number; readonly isLoading: boolean }) {
  const offset = CIRCLE_CIRCUMFERENCE - (score / 100) * CIRCLE_CIRCUMFERENCE;

  return (
    <div className="relative flex items-center justify-center">
      <svg width="120" height="120" viewBox="0 0 100 100" className="-rotate-90">
        {/* Background ring */}
        <circle
          cx="50"
          cy="50"
          r={CIRCLE_RADIUS}
          fill="none"
          stroke="currentColor"
          strokeWidth="6"
          className="text-muted/20"
        />
        {/* Progress ring */}
        <circle
          cx="50"
          cy="50"
          r={CIRCLE_RADIUS}
          fill="none"
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={CIRCLE_CIRCUMFERENCE}
          strokeDashoffset={isLoading ? CIRCLE_CIRCUMFERENCE : offset}
          className={`${getScoreRingColor(score)} transition-all duration-1000 ease-out`}
        />
      </svg>
      {/* Center text */}
      <div className="absolute flex flex-col items-center">
        <span className={`text-2xl font-bold ${isLoading ? "animate-pulse text-muted-foreground" : getScoreColor(score)}`}>
          {isLoading ? "..." : score}
        </span>
        <span className="text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
          {isLoading ? "Loading" : getScoreLabel(score)}
        </span>
      </div>
    </div>
  );
}

/* ── Component ────────────────────────────────────────────── */

export function CareerDnaReadiness({
  score,
  dimensions,
  isLoading = false,
}: CareerDnaReadinessProps) {
  return (
    <Card>
      <CardHeader className="text-center">
        <CardTitle className="text-lg">Career DNA Readiness Score™</CardTitle>
        <CardDescription>
          How ready your profile is for intelligent career guidance
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Circular score */}
        <div className="flex justify-center">
          <CircularScore score={score} isLoading={isLoading} />
        </div>

        {/* Dimension grid */}
        <div className="grid gap-3 sm:grid-cols-2">
          {dimensions.map((dimension) => (
            <div
              key={dimension.name}
              className="flex items-center gap-2 rounded-lg border border-border/50 px-3 py-2"
            >
              <span className="text-lg">{dimension.icon}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium">{dimension.name}</p>
              </div>
              <Badge
                variant={getCompletenessVariant(dimension.completeness)}
                className="shrink-0 text-[10px]"
              >
                {getCompletenessLabel(dimension.completeness)}
              </Badge>
            </div>
          ))}
        </div>

        {/* Score explanation */}
        {!isLoading && score < 80 && (
          <p className="text-center text-xs text-muted-foreground">
            Complete more profile dimensions to improve your readiness score and
            unlock deeper career insights.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
