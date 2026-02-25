"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  getFunnelMetrics,
  getMarketInsights,
  listExperiments,
  generateInsight,
} from "@/lib/api-client/analytics";
import type {
  FunnelMetricsResponse,
  MarketInsightsListResponse,
  CVExperimentsListResponse,
  InsightType,
} from "@/types/api/analytics";

/* ── Stage config ──────────────────────────────────────────── */

const STAGE_LABELS: Record<string, string> = {
  viewed: "Viewed",
  saved: "Saved",
  cv_tailored: "CV Tailored",
  applied: "Applied",
  interviewing: "Interviewing",
  offered: "Offered",
  accepted: "Accepted",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
};

const STAGE_COLORS: Record<string, string> = {
  viewed: "bg-blue-500",
  saved: "bg-indigo-500",
  cv_tailored: "bg-violet-500",
  applied: "bg-purple-500",
  interviewing: "bg-amber-500",
  offered: "bg-emerald-500",
  accepted: "bg-green-600",
  rejected: "bg-red-500",
  withdrawn: "bg-gray-400",
};

const INSIGHT_CONFIG: Record<
  InsightType,
  { label: string; icon: string; description: string }
> = {
  skill_demand: {
    label: "Skill Demand",
    icon: "📊",
    description: "Top skills in your matched listings",
  },
  salary_trend: {
    label: "Salary Trends",
    icon: "💰",
    description: "Salary data from your market segment",
  },
  market_heat: {
    label: "Market Heat",
    icon: "🔥",
    description: "New listing velocity in your domain",
  },
  competition_level: {
    label: "Competition",
    icon: "⚔️",
    description: "Estimated competition for your roles",
  },
  application_velocity: {
    label: "Your Velocity",
    icon: "🚀",
    description: "Your application rate over time",
  },
};

/* ── Main Page ─────────────────────────────────────────────── */

export default function AnalyticsPage() {
  const [funnel, setFunnel] = useState<FunnelMetricsResponse | null>(null);
  const [insights, setInsights] = useState<MarketInsightsListResponse | null>(
    null,
  );
  const [experiments, setExperiments] =
    useState<CVExperimentsListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generating, setGenerating] = useState<InsightType | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [funnelData, insightData, expData] = await Promise.all([
        getFunnelMetrics("30d"),
        getMarketInsights(),
        listExperiments(),
      ]);
      setFunnel(funnelData);
      setInsights(insightData);
      setExperiments(expData);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to load analytics",
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleGenerate = async (type: InsightType) => {
    setGenerating(type);
    try {
      await generateInsight(type, "30d");
      const updated = await getMarketInsights();
      setInsights(updated);
    } catch {
      /* silently handle */
    } finally {
      setGenerating(null);
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Career Analytics
          </h1>
          <p className="text-muted-foreground">
            Funnel pipeline, market intelligence, and CV optimization insights.
          </p>
        </div>
        <Link href="/dashboard">
          <Button variant="outline" size="sm">
            ← Dashboard
          </Button>
        </Link>
      </div>

      {/* Error state */}
      {error && (
        <Card className="border-destructive/30 bg-destructive/5">
          <CardContent className="flex items-center gap-3 py-4">
            <span className="text-2xl">⚠️</span>
            <div className="flex-1">
              <p className="text-sm font-medium text-destructive">{error}</p>
              <p className="text-xs text-muted-foreground">
                Make sure the API server is running and you are authenticated.
              </p>
            </div>
            <Button variant="outline" size="sm" onClick={loadData}>
              Retry
            </Button>
          </CardContent>
        </Card>
      )}

      {/* Loading skeleton */}
      {loading && (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <Card key={i}>
              <CardContent className="py-8">
                <div className="animate-pulse space-y-3">
                  <div className="h-4 w-1/3 rounded bg-muted" />
                  <div className="h-3 w-2/3 rounded bg-muted" />
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* ── Section 1: Application Funnel ───────────────── */}
      {!loading && funnel && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="text-2xl">🔽</span> Application Funnel
            </CardTitle>
            <CardDescription>
              Conversion rates across your application lifecycle — last{" "}
              {funnel.period}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {funnel.total_events === 0 ? (
              <div className="flex flex-col items-center gap-3 py-8 text-center">
                <span className="text-4xl">📈</span>
                <p className="text-sm text-muted-foreground">
                  No funnel events yet. Start applying to jobs to see your
                  conversion pipeline.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                {funnel.stages
                  .filter((s) =>
                    [
                      "viewed",
                      "saved",
                      "cv_tailored",
                      "applied",
                      "interviewing",
                      "offered",
                    ].includes(s.stage),
                  )
                  .map((stage) => (
                    <div key={stage.stage} className="space-y-1">
                      <div className="flex items-center justify-between text-sm">
                        <span className="font-medium">
                          {STAGE_LABELS[stage.stage] ?? stage.stage}
                        </span>
                        <span className="text-muted-foreground">
                          {stage.count} ({stage.conversion_rate}%)
                        </span>
                      </div>
                      <div className="h-3 w-full overflow-hidden rounded-full bg-muted">
                        <div
                          className={`h-full rounded-full transition-all duration-500 ${STAGE_COLORS[stage.stage] ?? "bg-primary"}`}
                          style={{
                            width: `${Math.max(stage.conversion_rate, 2)}%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                <div className="mt-4 flex items-center gap-2 text-xs text-muted-foreground">
                  <Badge variant="secondary">{funnel.total_events}</Badge>
                  <span>total events tracked</span>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* ── Section 2: Market Intelligence ──────────────── */}
      {!loading && insights && (
        <div>
          <h2 className="mb-4 text-xl font-semibold flex items-center gap-2">
            <span className="text-2xl">🌐</span> Market Intelligence
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {(Object.keys(INSIGHT_CONFIG) as InsightType[]).map((type) => {
              const config = INSIGHT_CONFIG[type];
              const existing = insights.insights.find(
                (i) => i.insight_type === type,
              );
              return (
                <Card
                  key={type}
                  className="transition-all duration-200 hover:shadow-md hover:border-primary/20"
                >
                  <CardHeader className="pb-2">
                    <CardTitle className="flex items-center gap-2 text-base">
                      <span className="text-xl">{config.icon}</span>
                      {config.label}
                    </CardTitle>
                    <CardDescription className="text-xs">
                      {config.description}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    {existing ? (
                      <div className="space-y-2">
                        <pre className="max-h-32 overflow-auto rounded bg-muted p-2 text-xs">
                          {JSON.stringify(existing.data, null, 2)}
                        </pre>
                        <p className="text-xs text-muted-foreground">
                          Generated:{" "}
                          {new Date(existing.generated_at).toLocaleDateString()}
                        </p>
                      </div>
                    ) : (
                      <div className="flex flex-col items-center gap-2 py-4">
                        <p className="text-xs text-muted-foreground">
                          No data yet
                        </p>
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={() => handleGenerate(type)}
                          disabled={generating === type}
                        >
                          {generating === type
                            ? "Generating..."
                            : "Generate Insight"}
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Section 3: CV A/B Experiments ───────────────── */}
      {!loading && experiments && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <span className="text-2xl">🧪</span> CV A/B Experiments
            </CardTitle>
            <CardDescription>
              Compare tailored CV versions to optimize application success
              rates.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {experiments.count === 0 ? (
              <div className="flex flex-col items-center gap-3 py-8 text-center">
                <span className="text-4xl">🔬</span>
                <p className="text-sm text-muted-foreground">
                  No experiments yet. Start an A/B test by tailoring two CV
                  versions for the same job.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left text-muted-foreground">
                      <th className="pb-2 pr-4 font-medium">Status</th>
                      <th className="pb-2 pr-4 font-medium">Hypothesis</th>
                      <th className="pb-2 pr-4 font-medium">Winner</th>
                      <th className="pb-2 font-medium">Created</th>
                    </tr>
                  </thead>
                  <tbody>
                    {experiments.experiments.map((exp) => (
                      <tr key={exp.id} className="border-b last:border-0">
                        <td className="py-3 pr-4">
                          <Badge
                            variant={
                              exp.status === "completed"
                                ? "default"
                                : exp.status === "running"
                                  ? "secondary"
                                  : "outline"
                            }
                            className={
                              exp.status === "completed"
                                ? "bg-green-600"
                                : undefined
                            }
                          >
                            {exp.status}
                          </Badge>
                        </td>
                        <td className="py-3 pr-4 max-w-[200px] truncate">
                          {exp.hypothesis ?? "—"}
                        </td>
                        <td className="py-3 pr-4">
                          {exp.winner_id ? (
                            <Badge
                              variant="default"
                              className="bg-emerald-600"
                            >
                              {exp.winner_id === exp.variant_a_id
                                ? "Variant A"
                                : "Variant B"}
                            </Badge>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </td>
                        <td className="py-3 text-muted-foreground">
                          {new Date(exp.created_at).toLocaleDateString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
