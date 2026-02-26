/**
 * PathForge — Career Threat Radar™ Dashboard Page
 * ==================================================
 * Full Threat Radar visualization sub-page with resilience score,
 * skills shield matrix, automation risk, and alert cards.
 *
 * Innovation: First consumer-facing career threat intelligence dashboard.
 * No competitor provides this to individual professionals.
 */

"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ScoreGauge } from "@/components/dashboard/score-gauge";
import { SkillsShieldMatrix } from "@/components/dashboard/skills-shield-matrix";
import { AlertCard } from "@/components/dashboard/alert-card";
import type { AlertStatus } from "@/types/api/threat-radar";
import {
  useThreatRadarOverview,
  useThreatRadarResilience,
  useThreatRadarSkillsShield,
  useThreatRadarAlerts,
  useTriggerThreatScan,
  useUpdateThreatAlert,
} from "@/hooks/api/use-threat-radar";

/* ── Helpers ──────────────────────────────────────────────── */

function getRiskBadgeVariant(riskLevel: string): "destructive" | "default" | "secondary" | "outline" {
  switch (riskLevel.toLowerCase()) {
    case "high":
    case "critical":
      return "destructive";
    case "medium":
      return "default";
    case "low":
      return "secondary";
    default:
      return "outline";
  }
}

function ResilienceBar({
  label,
  value,
}: {
  readonly label: string;
  readonly value: number;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span className="text-xs font-semibold">{Math.round(value)}</span>
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

export default function ThreatRadarPage() {
  const [alertPage, setAlertPage] = useState(1);

  const { data: overview, isLoading: overviewLoading } = useThreatRadarOverview();
  const { data: resilience, isLoading: resilienceLoading } = useThreatRadarResilience();
  const { data: skillsShield, isLoading: skillsShieldLoading } = useThreatRadarSkillsShield();
  const { data: alerts, isLoading: alertsLoading } = useThreatRadarAlerts(alertPage);
  const triggerScan = useTriggerThreatScan();
  const updateAlert = useUpdateThreatAlert();

  const handleAlertStatusChange = (alertId: string, newStatus: string): void => {
    updateAlert.mutate({
      alertId,
      data: { status: newStatus as AlertStatus },
    });
  };

  const totalPages = alerts ? Math.ceil(alerts.total / alerts.per_page) : 0;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Career Threat Radar™</h1>
          <p className="text-sm text-muted-foreground">
            Proactive career intelligence — threats, opportunities, and skill protection
          </p>
        </div>
        <Button
          onClick={() => triggerScan.mutate({ socCode: "15-1256", industryName: "Technology" })}
          disabled={triggerScan.isPending}
          size="sm"
        >
          {triggerScan.isPending ? "Scanning…" : "🔍 Run New Scan"}
        </Button>
      </div>

      {/* Row 1: Overview Stats */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent className="p-4 text-center">
            {overviewLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <>
                <p className="text-3xl font-bold">
                  {overview?.automation_risk?.overall_risk_score ?? "—"}
                </p>
                <p className="text-sm text-muted-foreground">Overall Risk Score</p>
                {overview?.automation_risk?.risk_level && (
                  <Badge variant={getRiskBadgeVariant(overview.automation_risk.risk_level)} className="mt-2">
                    {overview.automation_risk.risk_level} Risk
                  </Badge>
                )}
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 text-center">
            {overviewLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <>
                <p className="text-3xl font-bold">
                  {overview?.alerts_summary.unread ?? 0}
                </p>
                <p className="text-sm text-muted-foreground">Unread Alerts</p>
              </>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4 text-center">
            {overviewLoading ? (
              <Skeleton className="h-16 w-full" />
            ) : (
              <>
                <p className="text-3xl font-bold">
                  {overview?.last_scan_at
                    ? new Date(overview.last_scan_at).toLocaleDateString()
                    : "Never"}
                </p>
                <p className="text-sm text-muted-foreground">Last Scan</p>
              </>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 2: Resilience Score + Career Moat */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Career Resilience Score */}
        <Card>
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-lg">Career Resilience Score™</CardTitle>
            <CardDescription>
              How future-proof is your career?
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {resilienceLoading ? (
              <div className="space-y-3">
                <Skeleton className="h-24 w-full" />
                <Skeleton className="h-4 w-full" />
                <Skeleton className="h-4 w-3/4" />
              </div>
            ) : resilience ? (
              <>
                <div className="flex justify-center">
                  <ScoreGauge
                    score={resilience.overall_score ?? 0}
                    label="Resilience Score"
                    subtitle="Composite of 5 factors"
                  />
                </div>
                <div className="space-y-3">
                  <ResilienceBar label="Adaptability" value={resilience.adaptability ?? 0} />
                  <ResilienceBar label="Skill Diversity" value={resilience.skill_diversity ?? 0} />
                  <ResilienceBar label="Market Alignment" value={resilience.market_alignment ?? 0} />
                  <ResilienceBar label="Learning Velocity" value={resilience.learning_velocity ?? 0} />
                  <ResilienceBar label="Network Strength" value={resilience.network_strength ?? 0} />
                </div>
              </>
            ) : (
              <p className="text-sm text-muted-foreground text-center py-8">
                Run a threat scan to generate your resilience score.
              </p>
            )}
          </CardContent>
        </Card>

        {/* Career Moat Score */}
        <Card>
          <CardHeader className="text-center pb-2">
            <CardTitle className="text-lg">Career Moat Score</CardTitle>
            <CardDescription>
              How hard are you to replace?
            </CardDescription>
          </CardHeader>
          <CardContent>
            {resilienceLoading ? (
              <div className="flex justify-center py-8">
                <Skeleton className="h-24 w-32" />
              </div>
            ) : (
              <div className="flex flex-col items-center gap-4 py-4">
                <ScoreGauge
                  score={resilience?.career_moat_score ?? 0}
                  label="Moat Strength"
                  subtitle="Based on skill uniqueness & market demand"
                />
                <p className="text-xs text-muted-foreground text-center max-w-xs">
                  Your career moat measures how defensible your professional position is
                  based on the uniqueness and replaceability of your skill combination.
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Row 3: Skills Shield Matrix */}
      <SkillsShieldMatrix
        shields={skillsShield?.shields ?? []}
        exposures={skillsShield?.exposures ?? []}
        protectionScore={skillsShield?.overall_protection_score ?? 0}
        isLoading={skillsShieldLoading}
      />

      {/* Row 4: Active Alerts */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🚨 Threat & Opportunity Alerts</CardTitle>
          <CardDescription>
            Proactive intelligence about changes affecting your career
          </CardDescription>
        </CardHeader>
        <CardContent>
          {alertsLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} className="h-28 w-full" />
              ))}
            </div>
          ) : alerts?.items && alerts.items.length > 0 ? (
            <div className="space-y-3">
              {alerts.items.map((alert) => (
                <AlertCard
                  key={alert.id}
                  alert={{
                    id: alert.id,
                    title: alert.title,
                    description: alert.description,
                    severity: alert.severity as "critical" | "high" | "medium" | "low",
                    status: alert.status === "unread" ? "active" : alert.status as "active" | "read" | "dismissed" | "snoozed",
                    recommendation: alert.recommendation,
                    created_at: alert.created_at,
                  }}
                  onStatusChange={handleAlertStatusChange}
                  isUpdating={updateAlert.isPending}
                />
              ))}

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="flex items-center justify-center gap-2 pt-4">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={alertPage <= 1}
                    onClick={() => setAlertPage((prev) => Math.max(1, prev - 1))}
                  >
                    ← Previous
                  </Button>
                  <span className="text-xs text-muted-foreground">
                    Page {alertPage} of {totalPages}
                  </span>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={alertPage >= totalPages}
                    onClick={() => setAlertPage((prev) => prev + 1)}
                  >
                    Next →
                  </Button>
                </div>
              )}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              No active alerts. Run a threat scan to detect career threats and opportunities.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
