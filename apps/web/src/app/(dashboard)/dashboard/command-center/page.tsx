/**
 * PathForge — Career Command Center™ Dashboard Page
 * ====================================================
 * Unified 12-engine dashboard with Career Vitals™ score.
 */

"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useCommandCenterDashboard,
  useCareerHealthSummary,
  useRefreshVitals,
} from "@/hooks/api/use-command-center";

/* ── Page Component ───────────────────────────────────────── */

export default function CommandCenterPage(): React.JSX.Element {
  const { data: dashboard, isLoading } = useCommandCenterDashboard();
  const { data: healthSummary } = useCareerHealthSummary();
  const refreshVitals = useRefreshVitals();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Command Center</h1>
          <p className="text-sm text-muted-foreground">
            Unified career intelligence across all 12 engines
          </p>
        </div>
        <Button
          onClick={() => refreshVitals.mutate()}
          disabled={refreshVitals.isPending}
          size="sm"
        >
          {refreshVitals.isPending ? "Refreshing…" : "🔄 Refresh Vitals"}
        </Button>
      </div>

      {/* Career Vitals Score */}
      <Card className="border-primary/20 bg-primary/5">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">🎛️ Career Vitals™ Score</CardTitle>
          <CardDescription>Composite health score across all intelligence engines</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <Skeleton className="h-20 w-full" />
          ) : dashboard ? (
            <div className="flex items-center gap-8">
              <div className="text-center">
                <p className="text-5xl font-bold text-primary">
                  {dashboard.vitals_snapshot?.career_health_score != null
                    ? Math.round(dashboard.vitals_snapshot.career_health_score)
                    : "—"}
                </p>
                <p className="text-xs text-muted-foreground mt-1">out of 100</p>
              </div>
              {healthSummary && (
                <div className="flex-1 space-y-1">
                  <p className="text-sm">{healthSummary.key_insights[0] ?? "No insights available"}</p>
                  <p className="text-xs text-muted-foreground">
                    Trend: {healthSummary.trend}
                  </p>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-4">
              Refresh vitals to compute your Career Vitals™ Score.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Engine Status Grid */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">⚡ Engine Status</CardTitle>
          <CardDescription>Real-time status of all intelligence engines</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {Array.from({ length: 12 }, (_, index) => (
                <Skeleton key={index} className="h-20 w-full" />
              ))}
            </div>
          ) : dashboard?.engines?.length ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-4">
              {dashboard.engines.map((engine) => (
                <div
                  key={engine.engine_name}
                  className="rounded-lg border p-3 text-center"
                >
                  <p className="text-sm font-medium">{engine.display_name}</p>
                  <p className={`text-xs mt-1 ${
                    engine.status === "active" ? "text-green-600" :
                    engine.status === "error" ? "text-red-600" :
                    "text-muted-foreground"
                  }`}>
                    {engine.status}
                  </p>
                  {engine.health_score != null && (
                    <p className="text-lg font-bold mt-1">{Math.round(engine.health_score)}</p>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Engine status will appear after first vitals refresh.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
