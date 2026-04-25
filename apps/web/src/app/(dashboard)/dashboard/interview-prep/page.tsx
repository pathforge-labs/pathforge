/**
 * PathForge — Interview Intelligence Dashboard Page
 * ====================================================
 * Interview preps, question generation, STAR examples, negotiation.
 */

"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useInterviewDashboard } from "@/hooks/api/use-interview-intelligence";

/* ── Page Component ───────────────────────────────────────── */

export default function InterviewPrepPage(): React.JSX.Element {
  const { data: dashboard, isLoading } = useInterviewDashboard();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Interview Prep</h1>
          <p className="text-sm text-muted-foreground">
            AI-powered interview preparation with Career DNA insights
          </p>
        </div>
        <Button size="sm">🎤 New Prep</Button>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Preps</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">{dashboard?.total_preps ?? 0}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Companies Covered</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">{Object.keys(dashboard?.company_counts ?? {}).length}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Prep List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">📋 Saved Preps</CardTitle>
          <CardDescription>Your interview preparation sessions</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} className="h-20 w-full" />
              ))}
            </div>
          ) : dashboard?.preps?.length ? (
            <div className="space-y-3">
              {dashboard.preps.map((prep) => (
                <div
                  key={prep.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div>
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-sm">{prep.company_name}</p>
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                        {prep.prep_depth}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{prep.target_role}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">
                      {Math.round(prep.confidence_score * 100)}% confidence
                    </p>
                    {prep.culture_alignment_score != null && (
                      <p className="text-xs text-muted-foreground">
                        {Math.round(prep.culture_alignment_score * 100)}% culture fit
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Create your first interview prep to get AI-generated questions, STAR examples, and negotiation scripts.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
