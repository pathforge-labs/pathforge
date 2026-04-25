/**
 * PathForge — Actions Dashboard Page (Recommendations & Workflows)
 * ==================================================================
 * Intelligence-to-action: recommendations with priority scoring + inline workflows.
 * Design decision: merged recommendations + workflows into single "Actions" page
 * to reinforce the intelligence → action mental model.
 */

"use client";

import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useRecommendationDashboard,
  useGenerateRecommendations,
} from "@/hooks/api/use-recommendations";
import {
  useWorkflowDashboard,
  useWorkflowDetail,
} from "@/hooks/api/use-workflows";
import { WorkflowModal } from "@/components/dashboard/workflow-modal";

/* ── Page Component ───────────────────────────────────────── */

export default function RecommendationsPage(): React.JSX.Element {
  const { data: recDashboard, isLoading: recLoading } = useRecommendationDashboard();
  const { data: workflowDashboard, isLoading: wfLoading } = useWorkflowDashboard();
  const generateRecs = useGenerateRecommendations();
  const [selectedWorkflowId, setSelectedWorkflowId] = useState<string | null>(null);
  const { data: selectedWorkflow } = useWorkflowDetail(selectedWorkflowId ?? "");

  const isLoading = recLoading || wfLoading;

  return (
    <>
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Actions</h1>
          <p className="text-sm text-muted-foreground">
            Priority-weighted recommendations from all intelligence engines
          </p>
        </div>
        <Button
          onClick={() => generateRecs.mutate({ batch_type: "manual" })}
          disabled={generateRecs.isPending}
          size="sm"
        >
          {generateRecs.isPending ? "Generating…" : "⚡ Generate Actions"}
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Pending Actions</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">{recDashboard?.total_pending ?? 0}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Completed</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">{recDashboard?.total_completed ?? 0}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Workflows</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">{workflowDashboard?.total_active ?? 0}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Recommendation Feed — sorted by priority_score */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🎯 Recommended Actions</CardTitle>
          <CardDescription>
            Actions sorted by Priority-Weighted Score™ (urgency × impact ÷ effort)
          </CardDescription>
        </CardHeader>
        <CardContent>
          {recLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 4 }, (_, index) => (
                <Skeleton key={index} className="h-24 w-full" />
              ))}
            </div>
          ) : recDashboard?.recent_recommendations?.length ? (
            <div className="space-y-3">
              {[...recDashboard.recent_recommendations]
                .sort((a, b) => b.priority_score - a.priority_score)
                .map((rec) => (
                  <div
                    key={rec.id}
                    className="rounded-lg border p-4"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <div className="flex items-center gap-2">
                          <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-bold ${
                            rec.priority_score >= 75 ? "bg-red-100 text-red-800" :
                            rec.priority_score >= 50 ? "bg-yellow-100 text-yellow-800" :
                            "bg-green-100 text-green-800"
                          }`}>
                            {Math.round(rec.priority_score)} priority
                          </span>
                          <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                            {rec.recommendation_type}
                          </span>
                          <span className="text-xs text-muted-foreground">
                            {rec.effort_level} effort
                          </span>
                        </div>
                        <p className="font-medium text-sm mt-2">{rec.title}</p>
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {Math.round(rec.confidence_score * 100)}% confidence
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Generate actions to get personalized, priority-weighted recommendations.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Active Workflows */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🔄 Active Workflows</CardTitle>
          <CardDescription>Automated career pipelines currently in progress</CardDescription>
        </CardHeader>
        <CardContent>
          {wfLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 2 }, (_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : workflowDashboard?.active_workflows?.length ? (
            <div className="space-y-3">
              {workflowDashboard.active_workflows.map((workflow) => (
                <div
                  key={workflow.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div>
                    <p className="font-medium text-sm">{workflow.name}</p>
                    <p className="text-xs text-muted-foreground">
                      {workflow.trigger_type} • {workflow.completed_steps}/{workflow.total_steps} steps
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-2 w-24 rounded-full bg-muted overflow-hidden">
                      <div
                        className="h-full rounded-full bg-primary transition-all"
                        style={{
                          width: workflow.total_steps > 0
                            ? `${(workflow.completed_steps / workflow.total_steps) * 100}%`
                            : "0%",
                        }}
                      />
                    </div>
                    <span className="text-xs text-muted-foreground">{workflow.workflow_status}</span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSelectedWorkflowId(workflow.id)}
                    >
                      View Details
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Workflows will be created automatically when you act on recommendations.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Disclaimer */}
      {recDashboard?.disclaimer && (
        <p className="text-xs text-muted-foreground text-center">{recDashboard.disclaimer}</p>
      )}
    </div>

      {/* Workflow Detail Modal (Sprint 36 WS-4) */}
      <WorkflowModal
        workflow={selectedWorkflow ?? null}
        isOpen={selectedWorkflowId !== null}
        onClose={() => setSelectedWorkflowId(null)}
      />
    </>
  );
}
