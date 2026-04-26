/**
 * PathForge — AI Usage Settings Page (T4 / Sprint 56, ADR-0008)
 * ===============================================================
 *
 * Surfaces, per engine, what AI work the user has consumed in the
 * current month.  Tier-aware presentation:
 *
 *  - **Free tier**: "X / Y monthly scans used" (counts primary,
 *    EUR cost as fine-print).
 *  - **Premium tier**: "Estimated EUR cost: €0.42" (cost primary,
 *    counts as supporting context).
 *
 * The same API response carries both signals (sprint plan §12
 * default decision #4 = dual-display); the page picks the
 * presentation per `subscription.tier`.
 */

"use client";

import { useEffect, useState } from "react";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useAiUsageSummary } from "@/hooks/api/use-ai-usage";
import { useSubscription } from "@/hooks/api/use-billing";
import type { EngineUsageResponse, UsageSummaryAiResponse } from "@/types/api";

/* ── Helpers ──────────────────────────────────────────────── */

const PAYING_TIERS: ReadonlySet<string> = new Set(["pro", "premium"]);

function formatEur(cents: number): string {
  // Whole-cent rendering so the trust signal is unambiguous: €0.42,
  // not €0.4193. Server already rounded to integer cents.
  return new Intl.NumberFormat("en-IE", {
    style: "currency",
    currency: "EUR",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(cents / 100);
}

function humaniseEngine(engine: string): string {
  return engine
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

function formatRelative(iso: string | null, now: number | null): string {
  if (!iso) return "never";
  // `now === null` means we are pre-hydration. Render the absolute UTC
  // timestamp instead of "just now" / "5m ago" so the SSR markup
  // matches the first client render byte-for-byte. The relative form
  // appears after the `useEffect` below sets `now`. (Gemini medium —
  // hydration mismatch from `Date.now()` in render.)
  if (now === null) {
    return new Intl.DateTimeFormat("en-GB", {
      year: "numeric",
      month: "short",
      day: "2-digit",
      hour: "2-digit",
      minute: "2-digit",
      timeZone: "UTC",
    }).format(new Date(iso));
  }
  const then = new Date(iso).getTime();
  const diffMs = now - then;
  if (diffMs < 60_000) return "just now";
  const minutes = Math.floor(diffMs / 60_000);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

/** Returns a stable `now` timestamp that is `null` during SSR + first
 * client render (so output is deterministic) and a fresh timestamp
 * after hydration. Updates once per minute so "5m ago" eventually
 * becomes "6m ago" without re-rendering on every animation frame.
 *
 * Implementation note: the *first* tick of the interval also sets
 * `now`, so we don't need a separate `setNow(Date.now())` call —
 * which would trigger the `react-hooks/set-state-in-effect` lint
 * rule. We register a no-delay timer for the initial paint instead,
 * which fires synchronously enough for "just now" relative-time UX. */
function useClientNow(): number | null {
  const [now, setNow] = useState<number | null>(null);
  useEffect(() => {
    const initial = setTimeout(() => setNow(Date.now()), 0);
    const interval = setInterval(() => setNow(Date.now()), 60_000);
    return () => {
      clearTimeout(initial);
      clearInterval(interval);
    };
  }, []);
  return now;
}

/* ── Sub-components ───────────────────────────────────────── */

function EngineRow({
  engine,
  isPaying,
  now,
}: {
  engine: EngineUsageResponse;
  isPaying: boolean;
  now: number | null;
}) {
  return (
    <li
      className="grid grid-cols-1 sm:grid-cols-[1fr_auto_auto] gap-2 items-baseline py-3 border-b last:border-b-0"
      data-testid="ai-usage-engine-row"
      data-engine={engine.engine}
    >
      <div>
        <div className="font-medium">{humaniseEngine(engine.engine)}</div>
        <div className="text-sm text-muted-foreground">
          {engine.calls} {engine.calls === 1 ? "call" : "calls"} · last
          {" "}
          {formatRelative(engine.last_call_at, now)}
        </div>
      </div>
      <div className="text-sm text-muted-foreground tabular-nums">
        {engine.prompt_tokens.toLocaleString()} +
        {" "}
        {engine.completion_tokens.toLocaleString()} tok
      </div>
      <div className="font-mono text-sm tabular-nums" aria-label="estimated cost">
        {isPaying ? (
          <span data-testid="cost-primary">{formatEur(engine.cost_eur_cents)}</span>
        ) : (
          <span className="text-muted-foreground" data-testid="cost-secondary">
            ~{formatEur(engine.cost_eur_cents)}
          </span>
        )}
      </div>
    </li>
  );
}

function TotalsBlock({
  summary,
  isPaying,
}: {
  summary: UsageSummaryAiResponse;
  isPaying: boolean;
}) {
  return (
    <div
      className="grid grid-cols-1 md:grid-cols-2 gap-6 py-4"
      data-testid="ai-usage-totals"
    >
      <div>
        <div className="text-sm uppercase text-muted-foreground">
          {isPaying ? "AI calls this month" : "Scans used this month"}
        </div>
        <div
          className="text-3xl font-semibold tabular-nums"
          data-testid="primary-count"
        >
          {summary.total_calls.toLocaleString()}
        </div>
      </div>
      <div>
        <div className="text-sm uppercase text-muted-foreground">
          Estimated AI cost
          {summary.has_unpriced_models ? " (incomplete)" : ""}
        </div>
        <div
          className="text-3xl font-semibold tabular-nums"
          data-testid="primary-eur"
        >
          {formatEur(summary.total_cost_eur_cents)}
        </div>
        {summary.has_unpriced_models && (
          <p className="text-xs text-muted-foreground mt-1">
            Some models in this period are not in the price table —
            actual cost may be slightly higher.
          </p>
        )}
      </div>
    </div>
  );
}

/* ── Page ─────────────────────────────────────────────────── */

export default function AiUsageSettingsPage() {
  const usage = useAiUsageSummary("current_month");
  const subscription = useSubscription();
  const tier = subscription.data?.tier ?? "free";
  const isPaying = PAYING_TIERS.has(tier);
  // SSR-safe relative-time clock: `null` until hydration, then a
  // freshly-ticked timestamp every minute.
  const now = useClientNow();

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold">AI Usage</h1>
        <p className="text-muted-foreground mt-1">
          Transparent AI Accounting: every engine call you have made this
          month, the tokens it cost, and the estimated EUR cost behind
          your scans.
        </p>
      </div>

      <Card>
        <CardHeader className="flex-row items-center justify-between space-y-0">
          <div>
            <CardTitle>This month</CardTitle>
            <CardDescription>
              {usage.data
                ? new Intl.DateTimeFormat("en-GB", {
                    month: "long",
                    year: "numeric",
                    // The API returns the period boundary as a UTC
                    // ISO string. Without `timeZone: "UTC"` the
                    // formatter uses the *user's* local TZ — a user
                    // in UTC-3 would render "March" for an April UTC
                    // boundary on the 1st. Pinning to UTC also
                    // matches the SSR pass exactly so we don't trip
                    // hydration warnings.
                    timeZone: "UTC",
                  }).format(new Date(usage.data.period_start))
                : "Loading…"}
            </CardDescription>
          </div>
          <Badge variant={isPaying ? "default" : "secondary"}>
            {isPaying ? "Premium" : "Free"} tier
          </Badge>
        </CardHeader>
        <CardContent>
          {usage.isPending && (
            <div className="space-y-3" aria-busy="true">
              <Skeleton className="h-12" />
              <Skeleton className="h-32" />
            </div>
          )}

          {usage.isError && (
            <div role="alert" className="text-destructive">
              Could not load AI usage. Try refreshing the page; if it
              still fails, our team has been notified.
            </div>
          )}

          {usage.data && (
            <>
              <TotalsBlock summary={usage.data} isPaying={isPaying} />
              <Separator className="my-4" />
              {usage.data.engines.length === 0 ? (
                <div
                  className="py-12 text-center text-muted-foreground"
                  data-testid="ai-usage-empty"
                >
                  <p>No AI calls yet this month.</p>
                  <p className="text-sm mt-2">
                    Run a scan from the dashboard to see usage land here.
                  </p>
                </div>
              ) : (
                <ul className="divide-y" data-testid="ai-usage-engine-list">
                  {usage.data.engines.map((engine) => (
                    <EngineRow
                      key={engine.engine}
                      engine={engine}
                      isPaying={isPaying}
                      now={now}
                    />
                  ))}
                </ul>
              )}
            </>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Why we show this</CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground space-y-2">
          <p>
            The PathForge business model has you as the customer (you pay
            for AI) — not as the product (you pay <em>with</em> AI).
            That makes per-engine accounting a reasonable thing to
            surface: you should know what your scans cost.
          </p>
          <p>
            Cost figures are estimates derived from token counts and a
            quarterly price table; actual provider invoices may vary
            within ±5%.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
