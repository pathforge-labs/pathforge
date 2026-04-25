/**
 * PathForge — Skills Health Dashboard Page
 * ===========================================
 * Skill freshness, velocity map, reskilling pathways.
 * User-facing name: "Skills Health" (backend: skill-decay)
 */

"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { IntelligenceCard } from "@/components/dashboard/intelligence-card";
import { HeadlineInsight } from "@/components/dashboard/headline-insight";
import { FreshnessIndicator } from "@/components/dashboard/freshness-indicator";
import { VelocityMap } from "@/components/dashboard/velocity-map";
import {
  useSkillDecayDashboard,
  useTriggerDecayScan,
} from "@/hooks/api/use-skill-decay";

/* ── Helpers ──────────────────────────────────────────────── */

function buildHeadlineMessage(
  freshness: { freshness_score: number; skill_name: string }[],
): string {
  const urgentSkills = freshness.filter((s) => s.freshness_score < 40);
  const warningSkills = freshness.filter(
    (s) => s.freshness_score >= 40 && s.freshness_score < 60,
  );

  if (urgentSkills.length > 0) {
    const topUrgent = urgentSkills[0].skill_name;
    return `${urgentSkills.length} skill${urgentSkills.length > 1 ? "s" : ""} need${urgentSkills.length === 1 ? "s" : ""} immediate attention. ${topUrgent} is most at risk of losing market relevance.`;
  }

  if (warningSkills.length > 0) {
    return `${warningSkills.length} skill${warningSkills.length > 1 ? "s are" : " is"} showing early signs of decay. Monitor and refresh to stay competitive.`;
  }

  return "All your skills are in good health. Keep up the great work!";
}

/* ── Page Component ───────────────────────────────────────── */

export default function SkillDecayPage(): React.JSX.Element {
  const { data: dashboard, isLoading } = useSkillDecayDashboard();
  const triggerScan = useTriggerDecayScan();

  const hasData = Boolean(dashboard?.freshness.length);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Skills Health</h1>
          <p className="text-sm text-muted-foreground">
            Track skill freshness, velocity, and growth pathways
          </p>
        </div>
        <Button
          onClick={() => triggerScan.mutate()}
          disabled={triggerScan.isPending}
          size="sm"
        >
          {triggerScan.isPending ? "Analyzing…" : "🔍 Run Analysis"}
        </Button>
      </div>

      {/* Headline Insight */}
      {hasData && dashboard && (
        <HeadlineInsight
          icon="💡"
          message={buildHeadlineMessage(dashboard.freshness)}
          variant={
            dashboard.freshness.some((s) => s.freshness_score < 40)
              ? "warning"
              : "success"
          }
        />
      )}

      {/* Freshness Grid */}
      <IntelligenceCard
        title="Skill Freshness"
        icon="🔋"
        isLoading={isLoading}
        hasData={hasData}
        lastScanAt={dashboard?.last_scan_at}
        emptyState={
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              Run your first skills analysis to see freshness scores for each of your skills.
            </p>
            <Button
              className="mt-4"
              size="sm"
              onClick={() => triggerScan.mutate()}
              disabled={triggerScan.isPending}
            >
              🔍 Analyze My Skills
            </Button>
          </div>
        }
      >
        {dashboard && <FreshnessIndicator skills={dashboard.freshness} />}
      </IntelligenceCard>

      {/* Velocity Map */}
      <IntelligenceCard
        title="Skill Velocity Map"
        icon="📈"
        isLoading={isLoading}
        hasData={Boolean(dashboard?.velocity.length)}
      >
        {dashboard && <VelocityMap velocities={dashboard.velocity} />}
      </IntelligenceCard>

      {/* Reskilling Pathways */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">📚 Reskilling Pathways</CardTitle>
          <CardDescription>
            Personalized learning recommendations to strengthen your skill portfolio
          </CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : dashboard?.reskilling_pathways?.length ? (
            <div className="space-y-3">
              {dashboard.reskilling_pathways.map((pathway) => (
                <div
                  key={pathway.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium text-sm">{pathway.target_skill}</p>
                    <p className="text-xs text-muted-foreground">
                      {pathway.current_level} → {pathway.target_level} • Priority: {pathway.priority}
                    </p>
                  </div>
                  {pathway.estimated_effort_hours != null && (
                    <span className="text-xs text-muted-foreground">
                      ~{pathway.estimated_effort_hours}h
                    </span>
                  )}
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Run a skills analysis to generate personalized reskilling pathways.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
