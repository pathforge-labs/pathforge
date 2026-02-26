/**
 * PathForge — Career DNA™ Dashboard Page
 * =========================================
 * Full Career DNA visualization sub-page with radar chart, dimension cards,
 * dynamic readiness score (R1 resolution), and skill genome detail.
 */

"use client";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { CareerDnaRadar, type RadarDimension } from "@/components/dashboard/career-dna-radar";
import { CareerDnaReadiness, DEFAULT_DIMENSIONS, type CareerDnaReadinessProps } from "@/components/career-dna-readiness";
import {
  useCareerDnaSummary,
  useSkillGenome,
  useExperienceBlueprint,
  useGrowthVector,
  useValuesProfile,
  useMarketPosition,
  useGenerateCareerDna,
} from "@/hooks/api/use-career-dna";
import { useThreatRadarResilience } from "@/hooks/api/use-threat-radar";

/* ── Types ────────────────────────────────────────────────── */

type DimensionCompleteness = "complete" | "partial" | "empty";

/* ── Helpers ──────────────────────────────────────────────── */

function computeReadinessScore(
  skillGenomeAvg: number,
  experienceScore: number,
  growthScore: number,
  valuesScore: number,
  marketScore: number,
  resilienceScore: number,
): number {
  const total = skillGenomeAvg + experienceScore + growthScore + valuesScore + marketScore + resilienceScore;
  return Math.round(total / 6);
}

function getDimensionCompleteness(value: number): DimensionCompleteness {
  if (value >= 50) return "complete";
  if (value > 0) return "partial";
  return "empty";
}

function ProgressBar({ value, label }: { readonly value: number; readonly label: string }) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-xs font-semibold">{Math.round(value)}%</span>
      </div>
      <div className="h-2 w-full rounded-full bg-muted/30">
        <div
          className="h-full rounded-full bg-primary transition-all duration-500"
          style={{ width: `${Math.max(0, Math.min(100, value))}%` }}
        />
      </div>
    </div>
  );
}

/* ── Page Component ───────────────────────────────────────── */

export default function CareerDnaPage() {
  const { isLoading: summaryLoading } = useCareerDnaSummary();
  const { data: skillGenome, isLoading: skillGenomeLoading } = useSkillGenome();
  const { data: experience, isLoading: experienceLoading } = useExperienceBlueprint();
  const { data: growth, isLoading: growthLoading } = useGrowthVector();
  const { data: values, isLoading: valuesLoading } = useValuesProfile();
  const { data: market, isLoading: marketLoading } = useMarketPosition();
  const { data: resilience, isLoading: resilienceLoading } = useThreatRadarResilience();
  const generateMutation = useGenerateCareerDna();

  const isAnyLoading = summaryLoading || skillGenomeLoading || experienceLoading
    || growthLoading || valuesLoading || marketLoading || resilienceLoading;

  /* ── Compute normalized dimension values ───────────────── */

  const skillGenomeAvg = skillGenome?.length
    ? skillGenome.reduce((sum, entry) => sum + (entry.proficiency_level ?? 0), 0) / skillGenome.length
    : 0;

  const experienceScore = experience?.industry_diversity ?? 0;
  const growthScore = growth?.momentum_score ?? 0;
  const valuesScore = values?.top_values?.length
    ? Math.min(100, (values.top_values.length / 5) * 100)
    : 0;
  const marketScore = market?.competitiveness_score ?? 0;
  const resilienceScore = resilience?.overall_score ?? 0;

  const dynamicReadinessScore = computeReadinessScore(
    skillGenomeAvg, experienceScore, growthScore, valuesScore, marketScore, resilienceScore,
  );

  /* ── Build radar dimensions ────────────────────────────── */

  const radarDimensions: RadarDimension[] = [
    { label: "Skills", value: skillGenomeAvg, icon: "🧬" },
    { label: "Experience", value: experienceScore, icon: "📐" },
    { label: "Growth", value: growthScore, icon: "📈" },
    { label: "Values", value: valuesScore, icon: "💎" },
    { label: "Market", value: marketScore, icon: "🎯" },
    { label: "Resilience", value: resilienceScore, icon: "🛡️" },
  ];

  /* ── Build readiness dimensions for R1 ─────────────────── */

  const readinessDimensions: CareerDnaReadinessProps["dimensions"] = [
    { name: "Skill Genome", icon: "🧬", completeness: getDimensionCompleteness(skillGenomeAvg) },
    { name: "Experience Blueprint", icon: "📐", completeness: getDimensionCompleteness(experienceScore) },
    { name: "Growth Vector", icon: "📈", completeness: getDimensionCompleteness(growthScore) },
    { name: "Values Profile", icon: "💎", completeness: getDimensionCompleteness(valuesScore) },
    { name: "Market Position", icon: "🎯", completeness: getDimensionCompleteness(marketScore) },
    { name: "Career Resilience", icon: "🛡️", completeness: getDimensionCompleteness(resilienceScore) },
  ];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Career DNA™</h1>
          <p className="text-sm text-muted-foreground">
            Your complete career profile across 6 dimensions
          </p>
        </div>
        <Button
          onClick={() => generateMutation.mutate(undefined)}
          disabled={generateMutation.isPending}
          size="sm"
        >
          {generateMutation.isPending ? "Regenerating…" : "🔄 Regenerate"}
        </Button>
      </div>

      {/* Row 1: Readiness Score (R1) + Radar Chart */}
      <div className="grid gap-6 lg:grid-cols-2">
        <CareerDnaReadiness
          score={dynamicReadinessScore}
          dimensions={isAnyLoading ? DEFAULT_DIMENSIONS : readinessDimensions}
          isLoading={isAnyLoading}
        />
        <CareerDnaRadar
          dimensions={radarDimensions}
          isLoading={isAnyLoading}
        />
      </div>

      {/* Row 2: Skill Genome Detail */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🧬 Skill Genome</CardTitle>
          <CardDescription>
            {skillGenome?.length ?? 0} skills analyzed — proficiency levels and market demand
          </CardDescription>
        </CardHeader>
        <CardContent>
          {skillGenomeLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }, (_, index) => (
                <Skeleton key={index} className="h-12 w-full" />
              ))}
            </div>
          ) : skillGenome && skillGenome.length > 0 ? (
            <div className="space-y-3">
              {skillGenome.slice(0, 10).map((skill) => (
                <div
                  key={skill.skill_name}
                  className="flex items-center gap-4 rounded-lg border border-border/50 px-4 py-3"
                >
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{skill.skill_name}</p>
                    <div className="mt-1 h-1.5 w-full rounded-full bg-muted/30">
                      <div
                        className="h-full rounded-full bg-primary transition-all duration-500"
                        style={{ width: `${Math.max(0, Math.min(100, skill.proficiency_level ?? 0))}%` }}
                      />
                    </div>
                  </div>
                  <Badge variant="outline" className="shrink-0 text-[10px]">
                    {Math.round(skill.proficiency_level ?? 0)}%
                  </Badge>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No skill genome data available. Generate your Career DNA to see your skills analysis.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Row 3: Dimension Cards */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {/* Experience Blueprint */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">📐 Experience Blueprint</CardTitle>
          </CardHeader>
          <CardContent>
            {experienceLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : experience ? (
              <div className="space-y-2">
                <ProgressBar value={experienceScore} label="Industry Diversity" />
                <p className="text-xs text-muted-foreground">
                  {experience.total_years ?? 0} years · {experience.career_pattern ?? "Analyzing…"}
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No data yet</p>
            )}
          </CardContent>
        </Card>

        {/* Growth Vector */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">📈 Growth Vector</CardTitle>
          </CardHeader>
          <CardContent>
            {growthLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : growth ? (
              <div className="space-y-2">
                <ProgressBar value={growthScore} label="Momentum Score" />
                <p className="text-xs text-muted-foreground">
                  Trajectory: {growth.trajectory_direction ?? "Analyzing…"}
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No data yet</p>
            )}
          </CardContent>
        </Card>

        {/* Values Profile */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">💎 Values Profile</CardTitle>
          </CardHeader>
          <CardContent>
            {valuesLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : values ? (
              <div className="space-y-2">
                <ProgressBar value={valuesScore} label="Values Alignment" />
                <div className="flex flex-wrap gap-1 mt-1">
                  {(values.top_values ?? []).slice(0, 4).map((value) => (
                    <Badge key={value} variant="secondary" className="text-[10px]">
                      {value}
                    </Badge>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No data yet</p>
            )}
          </CardContent>
        </Card>

        {/* Market Position */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">🎯 Market Position</CardTitle>
          </CardHeader>
          <CardContent>
            {marketLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-4 w-3/4" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : market ? (
              <div className="space-y-2">
                <ProgressBar value={marketScore} label="Competitiveness" />
                <p className="text-xs text-muted-foreground">
                  Demand: {market.demand_level ?? "Analyzing…"}
                </p>
              </div>
            ) : (
              <p className="text-xs text-muted-foreground">No data yet</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
