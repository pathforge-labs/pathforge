/**
 * PathForge — Hidden Job Market Dashboard Page
 * ===============================================
 * Signal feed, opportunity radar, company scanning.
 */

"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  useHiddenJobMarketDashboard,
  useScanCompany,
  useOpportunities,
} from "@/hooks/api/use-hidden-job-market";

/* ── Page Component ───────────────────────────────────────── */

export default function HiddenJobMarketPage(): React.JSX.Element {
  const { data: dashboard, isLoading } = useHiddenJobMarketDashboard();
  const { data: opportunities } = useOpportunities();
  const scanCompany = useScanCompany();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Hidden Market</h1>
          <p className="text-sm text-muted-foreground">
            Detect pre-listing opportunities from company growth signals
          </p>
        </div>
        <Button
          onClick={() => scanCompany.mutate({ company_name: "" })}
          disabled={scanCompany.isPending}
          size="sm"
        >
          {scanCompany.isPending ? "Scanning…" : "🕵️ Scan Company"}
        </Button>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Total Signals</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">{dashboard?.total_signals ?? 0}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Active Signals</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">{dashboard?.active_signals ?? 0}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Avg Match</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">
                {dashboard?.average_match_score != null ? `${Math.round(dashboard.average_match_score * 100)}%` : "—"}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Signal Feed */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">📡 Signal Feed</CardTitle>
          <CardDescription>Company growth signals detected by AI analysis</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} className="h-20 w-full" />
              ))}
            </div>
          ) : dashboard?.signals?.length ? (
            <div className="space-y-3">
              {dashboard.signals.map((signal) => (
                <div
                  key={signal.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="font-medium text-sm">{signal.company_name}</p>
                      <span className="rounded-full bg-primary/10 px-2 py-0.5 text-xs font-medium text-primary">
                        {signal.signal_type}
                      </span>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{signal.title}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">
                      {Math.round(signal.strength * 100)}% strength
                    </p>
                    <p className="text-xs text-muted-foreground">{signal.status}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Scan a company or industry to start detecting hidden opportunities.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Opportunity Radar */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🎯 Opportunity Radar</CardTitle>
          <CardDescription>Pre-listing opportunities surfaced from signal analysis</CardDescription>
        </CardHeader>
        <CardContent>
          {opportunities?.opportunities?.length ? (
            <div className="space-y-3">
              {opportunities.opportunities.map((opp) => (
                <div
                  key={opp.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium text-sm">{opp.predicted_role}</p>
                    <p className="text-xs text-muted-foreground">
                      {opp.predicted_department} • {opp.time_horizon}
                    </p>
                  </div>
                  <span className="text-sm font-medium text-primary">
                    {Math.round(opp.probability * 100)}% likely
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Opportunities will appear here after signal analysis.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Disclaimer */}
      {dashboard?.disclaimer && (
        <p className="text-xs text-muted-foreground text-center">{dashboard.disclaimer}</p>
      )}
    </div>
  );
}
