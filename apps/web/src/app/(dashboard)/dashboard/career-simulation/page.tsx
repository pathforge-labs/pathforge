/**
 * PathForge — Career Simulator Dashboard Page
 * ===============================================
 * What-if career scenarios with 5 scenario types.
 * User-facing name: "Career Simulator" (backend: career-simulation)
 */

"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { IntelligenceCard } from "@/components/dashboard/intelligence-card";
import { HeadlineInsight } from "@/components/dashboard/headline-insight";
import { SimulationCard } from "@/components/dashboard/simulation-card";
import {
  useSimulationDashboard,
  useDeleteSimulation,
} from "@/hooks/api/use-career-simulation";

/* ── Helpers ──────────────────────────────────────────────── */

function buildSimulationHeadline(
  totalSimulations: number,
  scenarioCounts: Record<string, number>,
): string {
  if (totalSimulations === 0) return "Start exploring career scenarios to see how different moves could shape your future.";

  const topType = Object.entries(scenarioCounts)
    .sort(([, a], [, b]) => b - a)[0];

  return `You've explored ${totalSimulations} career scenario${totalSimulations > 1 ? "s" : ""}. ${topType ? `Most explored: ${topType[0].replace(/_/g, " ")} (${topType[1]}).` : ""}`;
}

/* ── Scenario Type Cards ─────────────────────────────────── */

const SCENARIO_TYPES = [
  { type: "role_transition", label: "Role Change", icon: "🎯", description: "Simulate transitioning to a new role" },
  { type: "geo_move", label: "Relocation", icon: "🌍", description: "What if you moved to a new location?" },
  { type: "skill_investment", label: "Skill Investment", icon: "📚", description: "Impact of learning new skills" },
  { type: "industry_pivot", label: "Industry Pivot", icon: "🔄", description: "Explore a new industry" },
  { type: "seniority_jump", label: "Seniority Jump", icon: "📈", description: "Move up the career ladder" },
] as const;

/* ── Page Component ───────────────────────────────────────── */

export default function CareerSimulationPage(): React.JSX.Element {
  const { data: dashboard, isLoading } = useSimulationDashboard();
  const deleteSimulation = useDeleteSimulation();

  const hasData = Boolean(dashboard?.total_simulations);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Career Simulator</h1>
        <p className="text-sm text-muted-foreground">
          Explore what-if scenarios to make informed career decisions
        </p>
      </div>

      {/* Headline Insight */}
      {dashboard && (
        <HeadlineInsight
          icon="🔮"
          message={buildSimulationHeadline(
            dashboard.total_simulations,
            dashboard.scenario_type_counts,
          )}
          variant={hasData ? "info" : "neutral"}
        />
      )}

      {/* Scenario Type Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">🎯 Run a New Scenario</CardTitle>
          <CardDescription>
            Choose a scenario type to simulate and explore outcomes
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {SCENARIO_TYPES.map((scenario) => (
              <div
                key={scenario.type}
                className="flex items-center gap-3 rounded-lg border p-3 hover:bg-muted/50 transition-colors cursor-pointer"
                role="button"
                tabIndex={0}
              >
                <span className="text-2xl" aria-hidden="true">{scenario.icon}</span>
                <div>
                  <p className="font-medium text-sm">{scenario.label}</p>
                  <p className="text-xs text-muted-foreground">{scenario.description}</p>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Simulation Results */}
      <IntelligenceCard
        title="Your Simulations"
        icon="📋"
        isLoading={isLoading}
        hasData={hasData}
        emptyState={
          <div className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              No simulations yet. Choose a scenario type above to run your first career simulation.
            </p>
          </div>
        }
      >
        {dashboard && dashboard.simulations.length > 0 && (
          <div className="grid gap-4 sm:grid-cols-2">
            {dashboard.simulations.map((simulation) => (
              <SimulationCard
                key={simulation.id}
                simulation={simulation}
                onDelete={(id) => deleteSimulation.mutate(id)}
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
              <p className="text-3xl font-bold">{dashboard.total_simulations}</p>
              <p className="text-sm text-muted-foreground">Total Simulations</p>
            </CardContent>
          </Card>
          {Object.entries(dashboard.scenario_type_counts)
            .sort(([, a], [, b]) => b - a)
            .slice(0, 2)
            .map(([type, count]) => (
              <Card key={type}>
                <CardContent className="p-4 text-center">
                  <p className="text-3xl font-bold">{count}</p>
                  <p className="text-sm text-muted-foreground">{type.replace(/_/g, " ")}</p>
                </CardContent>
              </Card>
            ))}
        </div>
      )}
    </div>
  );
}
