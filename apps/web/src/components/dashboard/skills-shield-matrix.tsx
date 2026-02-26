/**
 * PathForge — Skills Shield™ Matrix
 * ====================================
 * Visual table separating skills into shields (protective) vs exposures (vulnerable).
 *
 * Innovation: First-to-market individual-facing skill vulnerability analysis.
 * Enterprise tools (Gloat Skills Planner) provide this only to HR teams.
 */

"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ScoreGauge } from "@/components/dashboard/score-gauge";

/* ── Types ────────────────────────────────────────────────── */

interface ShieldSkill {
  readonly skill_name: string;
  readonly automation_resistance: number;
  readonly market_demand: number;
  readonly recommendation: string | null;
}

export interface SkillsShieldMatrixProps {
  readonly shields: readonly ShieldSkill[];
  readonly exposures: readonly ShieldSkill[];
  readonly protectionScore: number;
  readonly isLoading?: boolean;
}

/* ── Helpers ──────────────────────────────────────────────── */

function ProgressBar({
  value,
  maxValue = 100,
  colorClass,
}: {
  readonly value: number;
  readonly maxValue?: number;
  readonly colorClass: string;
}) {
  const percentage = Math.max(0, Math.min(100, (value / maxValue) * 100));
  return (
    <div className="h-1.5 w-full rounded-full bg-muted/30">
      <div
        className={`h-full rounded-full transition-all duration-500 ${colorClass}`}
        style={{ width: `${percentage}%` }}
      />
    </div>
  );
}

/* ── Skill Row ────────────────────────────────────────────── */

function SkillRow({
  skill,
  variant,
}: {
  readonly skill: ShieldSkill;
  readonly variant: "shield" | "exposure";
}) {
  const isShield = variant === "shield";
  return (
    <div className={`rounded-lg border px-3 py-2.5 space-y-1.5 ${
      isShield
        ? "border-green-500/20 bg-green-500/5"
        : "border-red-500/20 bg-red-500/5"
    }`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium">{skill.skill_name}</span>
        <Badge
          variant={isShield ? "default" : "destructive"}
          className="text-[9px] h-4"
        >
          {isShield ? "✅ Shield" : "⚠️ Exposed"}
        </Badge>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div>
          <p className="text-[9px] text-muted-foreground mb-0.5">AI Resistance</p>
          <ProgressBar
            value={skill.automation_resistance}
            colorClass={isShield ? "bg-green-500" : "bg-red-400"}
          />
        </div>
        <div>
          <p className="text-[9px] text-muted-foreground mb-0.5">Market Demand</p>
          <ProgressBar
            value={skill.market_demand}
            colorClass={isShield ? "bg-emerald-400" : "bg-orange-400"}
          />
        </div>
      </div>

      {skill.recommendation && (
        <p className="text-[10px] text-muted-foreground italic">
          💡 {skill.recommendation}
        </p>
      )}
    </div>
  );
}

/* ── Component ────────────────────────────────────────────── */

export function SkillsShieldMatrix({
  shields,
  exposures,
  protectionScore,
  isLoading = false,
}: SkillsShieldMatrixProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Skills Shield™ Matrix</CardTitle>
          <CardDescription>Analyzing your skill protection…</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <Skeleton className="h-24 w-full" />
          <div className="grid gap-3 sm:grid-cols-2">
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
            <Skeleton className="h-20" />
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="text-center pb-2">
        <CardTitle className="text-lg">Skills Shield™ Matrix</CardTitle>
        <CardDescription>
          Which skills protect you vs. expose you to disruption
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Protection Score Gauge */}
        <div className="flex justify-center">
          <ScoreGauge
            score={protectionScore}
            label="Protection Score"
            subtitle={`${shields.length} shields · ${exposures.length} exposures`}
          />
        </div>

        {/* Two-column matrix */}
        <div className="grid gap-4 sm:grid-cols-2">
          {/* Shields column */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-green-600 dark:text-green-400 uppercase tracking-wider">
              ✅ Shields ({shields.length})
            </h4>
            {shields.length === 0 && (
              <p className="text-xs text-muted-foreground italic py-2">
                No shield skills detected yet.
              </p>
            )}
            {shields.map((skill) => (
              <SkillRow
                key={skill.skill_name}
                skill={skill}
                variant="shield"
              />
            ))}
          </div>

          {/* Exposures column */}
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-red-600 dark:text-red-400 uppercase tracking-wider">
              ⚠️ Exposures ({exposures.length})
            </h4>
            {exposures.length === 0 && (
              <p className="text-xs text-muted-foreground italic py-2">
                No skill exposures detected — great!
              </p>
            )}
            {exposures.map((skill) => (
              <SkillRow
                key={skill.skill_name}
                skill={skill}
                variant="exposure"
              />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
