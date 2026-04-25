/**
 * PathForge — Career Passport Dashboard Page
 * =============================================
 * Credential mapping, country comparison, visa assessment.
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useCareerPassportDashboard } from "@/hooks/api/use-career-passport";

/* ── Page Component ───────────────────────────────────────── */

export default function CareerPassportPage(): React.JSX.Element {
  const { data: dashboard, isLoading } = useCareerPassportDashboard();

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Career Passport</h1>
        <p className="text-sm text-muted-foreground">
          Cross-border credential mapping, country comparison, and visa assessment
        </p>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Credential Mappings</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">{dashboard?.total_mappings ?? 0}</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium text-muted-foreground">Country Comparisons</CardTitle>
          </CardHeader>
          <CardContent>
            {isLoading ? <Skeleton className="h-8 w-16" /> : (
              <p className="text-2xl font-bold">{dashboard?.total_comparisons ?? 0}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Credential Mappings */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🎓 Credential Mappings</CardTitle>
          <CardDescription>International equivalency mappings for your qualifications</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 3 }, (_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : dashboard?.credential_mappings?.length ? (
            <div className="space-y-3">
              {dashboard.credential_mappings.map((mapping) => (
                <div
                  key={mapping.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div>
                    <p className="font-medium text-sm">{mapping.source_qualification}</p>
                    <p className="text-xs text-muted-foreground">
                      {mapping.source_country} → {mapping.target_country}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">{mapping.equivalent_level}</p>
                    <p className="text-xs text-muted-foreground">EQF: {mapping.eqf_level}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Add your qualifications to see international equivalency mappings.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Country Comparisons */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🌍 Country Comparisons</CardTitle>
          <CardDescription>Side-by-side career mobility analysis</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 2 }, (_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : dashboard?.country_comparisons?.length ? (
            <div className="space-y-3">
              {dashboard.country_comparisons.map((comparison) => (
                <div
                  key={comparison.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div>
                    <p className="font-medium text-sm">
                      {comparison.source_country} → {comparison.target_country}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      CoL Index: {comparison.cost_of_living_index} • Demand: {comparison.market_demand_level}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-medium">
                      {comparison.salary_delta_pct > 0 ? "+" : ""}{Math.round(comparison.salary_delta_pct)}% salary
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {comparison.purchasing_power_delta > 0 ? "+" : ""}{Math.round(comparison.purchasing_power_delta)}% buying power
                    </p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Compare countries to understand salary, cost of living, and career mobility differences.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Visa Assessments */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🛂 Visa Assessments</CardTitle>
          <CardDescription>Work permit feasibility for target countries</CardDescription>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-3">
              {Array.from({ length: 2 }, (_, index) => (
                <Skeleton key={index} className="h-16 w-full" />
              ))}
            </div>
          ) : dashboard?.visa_assessments?.length ? (
            <div className="space-y-3">
              {dashboard.visa_assessments.map((visa) => (
                <div
                  key={visa.id}
                  className="flex items-center justify-between rounded-lg border p-4"
                >
                  <div>
                    <p className="font-medium text-sm">{visa.target_country} — {visa.visa_type}</p>
                    <p className="text-xs text-muted-foreground">
                      Nationality: {visa.nationality}
                      {visa.processing_time_weeks != null && ` • ~${visa.processing_time_weeks} weeks`}
                    </p>
                  </div>
                  <p className="text-sm font-medium">
                    {Math.round(visa.eligibility_score * 100)}% eligible
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-muted-foreground text-center py-8">
              Assess visa feasibility for your target countries.
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
