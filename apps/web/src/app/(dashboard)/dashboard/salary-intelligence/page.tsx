/**
 * PathForge — Salary Intelligence Dashboard Page
 * =================================================
 * Salary range, skill impacts, trajectory, and what-if scenarios.
 * User-facing name: "Salary Intelligence"
 */

"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { IntelligenceCard } from "@/components/dashboard/intelligence-card";
import { HeadlineInsight } from "@/components/dashboard/headline-insight";
import { SalaryRangeBar } from "@/components/dashboard/salary-range-bar";
import { SkillImpactChart } from "@/components/dashboard/skill-impact-chart";
import {
  useSalaryDashboard,
  useTriggerSalaryScan,
} from "@/hooks/api/use-salary-intelligence";

/* ── Helpers ──────────────────────────────────────────────── */

function formatCurrency(amount: number, currency: string): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

function buildSalaryHeadline(
  estimate: { estimated_median: number; currency: string; market_percentile: number | null } | null,
  impacts: { salary_impact_amount: number; skill_name: string; impact_direction: string }[],
): string {
  if (!estimate) return "Run your first salary scan to get personalized earnings intelligence.";

  const topPositive = impacts
    .filter((i) => i.impact_direction === "positive")
    .sort((a, b) => b.salary_impact_amount - a.salary_impact_amount)[0];

  const percentileText = estimate.market_percentile != null
    ? ` You're in the ${Math.round(estimate.market_percentile)}th percentile for your role.`
    : "";

  const skillText = topPositive
    ? ` ${topPositive.skill_name} is your highest-value skill, adding ${formatCurrency(topPositive.salary_impact_amount, estimate.currency)}/year.`
    : "";

  return `Your estimated market salary is ${formatCurrency(estimate.estimated_median, estimate.currency)}.${percentileText}${skillText}`;
}

/* ── Page Component ───────────────────────────────────────── */

export default function SalaryIntelligencePage(): React.JSX.Element {
  const { data: dashboard, isLoading } = useSalaryDashboard();
  const triggerScan = useTriggerSalaryScan();

  const hasData = Boolean(dashboard?.estimate);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Salary Intelligence</h1>
          <p className="text-sm text-muted-foreground">
            Personalized earnings analysis with skill impact modeling
          </p>
        </div>
        <Button
          onClick={() => triggerScan.mutate()}
          disabled={triggerScan.isPending}
          size="sm"
        >
          {triggerScan.isPending ? "Analyzing…" : "💰 Run Analysis"}
        </Button>
      </div>

      {/* Headline Insight */}
      {hasData && dashboard && (
        <HeadlineInsight
          icon="💰"
          message={buildSalaryHeadline(dashboard.estimate, dashboard.skill_impacts)}
          variant="info"
        />
      )}

      {/* Salary Range */}
      <IntelligenceCard
        title="Salary Estimate"
        icon="💵"
        isLoading={isLoading}
        hasData={hasData}
        lastScanAt={dashboard?.last_scan_at}
        emptyState={
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              Run your first salary analysis to get a personalized earnings estimate based on your Career DNA.
            </p>
            <Button
              className="mt-4"
              size="sm"
              onClick={() => triggerScan.mutate()}
              disabled={triggerScan.isPending}
            >
              💰 Analyze My Salary
            </Button>
          </div>
        }
      >
        {dashboard?.estimate && <SalaryRangeBar estimate={dashboard.estimate} />}
      </IntelligenceCard>

      {/* Skill Impact */}
      <IntelligenceCard
        title="Skill Salary Impact"
        icon="📊"
        isLoading={isLoading}
        hasData={Boolean(dashboard?.skill_impacts.length)}
      >
        {dashboard && (
          <SkillImpactChart
            impacts={dashboard.skill_impacts}
            currency={dashboard.estimate?.currency ?? "EUR"}
          />
        )}
      </IntelligenceCard>

      {/* Salary Trajectory */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">📈 Salary Trajectory</CardTitle>
          <CardDescription>
            Historical salary progression over time
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-32 w-full" />
          ) : dashboard?.trajectory.length ? (
            <div className="space-y-2">
              {dashboard.trajectory.slice(0, 5).map((entry) => (
                <div
                  key={entry.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium text-sm">{entry.role_title}</p>
                    <p className="text-xs text-muted-foreground">
                      {entry.location} • {entry.seniority_level}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-sm">
                      {formatCurrency(entry.estimated_median, entry.currency)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(entry.snapshot_date).toLocaleDateString("en-US", {
                        month: "short",
                        year: "numeric",
                      })}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Run multiple salary scans over time to build your trajectory.
            </p>
          )}
        </CardContent>
      </Card>

      {/* What-If Scenarios */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🔮 What-If Scenarios</CardTitle>
          <CardDescription>
            Explore how changes could impact your earnings
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-24 w-full" />
          ) : dashboard?.scenarios.length ? (
            <div className="space-y-2">
              {dashboard.scenarios.map((scenario) => (
                <div
                  key={scenario.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium text-sm">{scenario.scenario_label}</p>
                    <p className="text-xs text-muted-foreground">{scenario.scenario_type}</p>
                  </div>
                  <div className="text-right">
                    <p className={`font-semibold text-sm ${scenario.delta_amount >= 0 ? "text-green-600" : "text-red-500"}`}>
                      {scenario.delta_amount >= 0 ? "+" : ""}
                      {formatCurrency(scenario.delta_amount, scenario.currency)}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {scenario.delta_percent >= 0 ? "+" : ""}{scenario.delta_percent.toFixed(1)}%
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No scenarios yet. Run a salary analysis first, then explore what-if scenarios.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
