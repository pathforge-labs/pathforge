/**
 * PathForge — Threat Alert Card
 * ===============================
 * Individual alert card with severity badge, action buttons, and
 * expandable description. Used in the Threat Radar dashboard.
 *
 * Innovation: No competitor pushes proactive career threat intelligence
 * to individual users. Enterprise tools keep alerts employer-facing.
 */

"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

/* ── Types ────────────────────────────────────────────────── */

type AlertSeverity = "critical" | "high" | "medium" | "low";
type AlertStatus = "active" | "read" | "dismissed" | "snoozed";

export interface AlertCardAlert {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly severity: AlertSeverity;
  readonly status: AlertStatus;
  readonly recommendation: string | null;
  readonly created_at: string;
}

export interface AlertCardProps {
  readonly alert: AlertCardAlert;
  readonly onStatusChange: (alertId: string, newStatus: AlertStatus) => void;
  readonly isUpdating?: boolean;
}

/* ── Helpers ──────────────────────────────────────────────── */

const SEVERITY_CONFIG: Record<AlertSeverity, { label: string; variant: "destructive" | "default" | "secondary" | "outline"; className: string }> = {
  critical: { label: "Critical", variant: "destructive", className: "bg-red-500/10 border-red-500/20" },
  high: { label: "High", variant: "destructive", className: "bg-orange-500/10 border-orange-500/20" },
  medium: { label: "Medium", variant: "secondary", className: "bg-yellow-500/10 border-yellow-500/20" },
  low: { label: "Low", variant: "outline", className: "bg-blue-500/10 border-blue-500/20" },
};

function formatRelativeTime(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return "Today";
  if (diffDays === 1) return "Yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)}w ago`;
  return `${Math.floor(diffDays / 30)}mo ago`;
}

/* ── Component ────────────────────────────────────────────── */

export function AlertCard({ alert, onStatusChange, isUpdating = false }: AlertCardProps) {
  const [expanded, setExpanded] = useState(false);
  const config = SEVERITY_CONFIG[alert.severity];
  const descriptionTruncated = alert.description.length > 120 && !expanded;

  return (
    <Card className={`transition-colors ${config.className}`}>
      <CardContent className="p-4 space-y-3">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <Badge variant={config.variant} className="shrink-0 text-[10px]">
                {config.label}
              </Badge>
              <span className="text-[10px] text-muted-foreground">
                {formatRelativeTime(alert.created_at)}
              </span>
            </div>
            <h4 className="text-sm font-semibold leading-snug">{alert.title}</h4>
          </div>
        </div>

        {/* Description */}
        <p className="text-xs text-muted-foreground leading-relaxed">
          {descriptionTruncated
            ? `${alert.description.slice(0, 120)}…`
            : alert.description}
          {alert.description.length > 120 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="ml-1 text-primary hover:underline font-medium"
              type="button"
            >
              {expanded ? "Show less" : "Show more"}
            </button>
          )}
        </p>

        {/* Recommendation */}
        {alert.recommendation && (
          <div className="rounded-md bg-background/50 px-3 py-2 border border-border/30">
            <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider mb-0.5">
              Recommendation
            </p>
            <p className="text-xs text-foreground">{alert.recommendation}</p>
          </div>
        )}

        {/* Action buttons */}
        {alert.status === "active" && (
          <div className="flex items-center gap-2 pt-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              disabled={isUpdating}
              onClick={() => onStatusChange(alert.id, "read")}
            >
              ✓ Mark Read
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              disabled={isUpdating}
              onClick={() => onStatusChange(alert.id, "snoozed")}
            >
              ⏰ Snooze
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs text-muted-foreground"
              disabled={isUpdating}
              onClick={() => onStatusChange(alert.id, "dismissed")}
            >
              ✕ Dismiss
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
