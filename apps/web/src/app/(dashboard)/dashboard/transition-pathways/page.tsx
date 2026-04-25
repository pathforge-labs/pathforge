/**
 * PathForge — Career Moves Dashboard Page
 * ==========================================
 * Transition pathways with skill bridges and milestones.
 * User-facing name: "Career Moves" (backend: transition-pathways)
 */

"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { IntelligenceCard } from "@/components/dashboard/intelligence-card";
import { HeadlineInsight } from "@/components/dashboard/headline-insight";
import { TransitionCard } from "@/components/dashboard/transition-card";
import {
  useTransitionDashboard,
  useDeleteTransition,
} from "@/hooks/api/use-transition-pathways";

/* ── Helpers ──────────────────────────────────────────────── */

function buildTransitionHeadline(
  transitions: { confidence_score: number; to_role: string; skill_overlap_percent: number }[],
  totalExplored: number,
): string {
  if (totalExplored === 0) {
    return "Start exploring career moves to see how realistic different transitions are for you.";
  }

  const bestFit = [...transitions]
    .sort((a, b) => b.confidence_score - a.confidence_score)[0];

  if (bestFit) {
    return `You've explored ${totalExplored} career move${totalExplored > 1 ? "s" : ""}. Your strongest match is ${bestFit.to_role} with ${Math.round(bestFit.confidence_score * 100)}% confidence and ${Math.round(bestFit.skill_overlap_percent)}% skill overlap.`;
  }

  return `You've explored ${totalExplored} career move${totalExplored > 1 ? "s" : ""}.`;
}

/* ── Page Component ───────────────────────────────────────── */

export default function TransitionPathwaysPage(): React.JSX.Element {
  const { data: dashboard, isLoading } = useTransitionDashboard();
  const deleteTransition = useDeleteTransition();

  const hasData = Boolean(dashboard?.transitions.length);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Career Moves</h1>
          <p className="text-sm text-muted-foreground">
            Explore transitions with skill bridges, milestones, and success probability
          </p>
        </div>
      </div>

      {/* Headline Insight */}
      {dashboard && (
        <HeadlineInsight
          icon="🔄"
          message={buildTransitionHeadline(
            dashboard.transitions,
            dashboard.total_explored,
          )}
          variant={hasData ? "info" : "neutral"}
        />
      )}

      {/* Explore New Transition */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🧭 Explore a New Move</CardTitle>
          <CardDescription>
            Enter a target role to explore the transition path, skill gaps, and timeline
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex gap-3">
            <div className="flex-1">
              <input
                type="text"
                placeholder="e.g., Data Engineer, Product Manager, Staff Engineer…"
                className="w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                aria-label="Target role"
                id="target-role-input"
              />
            </div>
            <Button size="sm">
              🔍 Explore
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Explored Transitions */}
      <IntelligenceCard
        title="Explored Transitions"
        icon="📋"
        isLoading={isLoading}
        hasData={hasData}
        emptyState={
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              No transitions explored yet. Enter a target role above to start exploring career moves.
            </p>
          </div>
        }
      >
        {dashboard && dashboard.transitions.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2">
            {dashboard.transitions.map((transition) => (
              <TransitionCard
                key={transition.id}
                transition={transition}
                onDelete={(id) => deleteTransition.mutate(id)}
              />
            ))}
          </div>
        )}
      </IntelligenceCard>

      {/* Stats */}
      {hasData && dashboard && (
        <div className="grid gap-4 sm:grid-cols-3">
          <Card>
            <CardContent className="p-4 text-center">
              <p className="text-3xl font-bold">{dashboard.total_explored}</p>
              <p className="text-sm text-muted-foreground">Moves Explored</p>
            </CardContent>
          </Card>
          {(() => {
            const avgConfidence = dashboard.transitions.reduce(
              (sum, t) => sum + t.confidence_score, 0
            ) / Math.max(dashboard.transitions.length, 1);
            return (
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-3xl font-bold">{Math.round(avgConfidence * 100)}%</p>
                  <p className="text-sm text-muted-foreground">Avg Confidence</p>
                </CardContent>
              </Card>
            );
          })()}
          {(() => {
            const avgOverlap = dashboard.transitions.reduce(
              (sum, t) => sum + t.skill_overlap_percent, 0
            ) / Math.max(dashboard.transitions.length, 1);
            return (
              <Card>
                <CardContent className="p-4 text-center">
                  <p className="text-3xl font-bold">{Math.round(avgOverlap)}%</p>
                  <p className="text-sm text-muted-foreground">Avg Skill Overlap</p>
                </CardContent>
              </Card>
            );
          })()}
        </div>
      )}
    </div>
  );
}
