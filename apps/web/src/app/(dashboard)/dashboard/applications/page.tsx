"use client";

import { useEffect, useState, useCallback } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  listApplications,
  updateApplicationStatus,
  deleteApplication,
} from "@/lib/api-client/applications";
import type { ApplicationResponse } from "@/types/api/applications";

const STATUS_CONFIG: Record<
  string,
  { label: string; color: string; icon: string }
> = {
  saved: { label: "Saved", color: "bg-slate-500", icon: "📌" },
  applied: { label: "Applied", color: "bg-blue-600", icon: "📨" },
  interviewing: { label: "Interviewing", color: "bg-amber-500", icon: "🎤" },
  offered: { label: "Offered", color: "bg-green-600", icon: "🎉" },
  rejected: { label: "Rejected", color: "bg-red-500", icon: "✖" },
  withdrawn: { label: "Withdrawn", color: "bg-gray-400", icon: "↩" },
};

const KANBAN_COLUMNS = ["saved", "applied", "interviewing", "offered", "rejected"];

export default function ApplicationsPage() {
  const [apps, setApps] = useState<ApplicationResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<string | null>(null);

  const fetchApps = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listApplications(
        activeFilter ?? undefined,
        1,
        100,
      );
      setApps(data.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load applications");
    } finally {
      setLoading(false);
    }
  }, [activeFilter]);

  useEffect(() => {
    fetchApps();
  }, [fetchApps]);

  const handleStatusUpdate = async (appId: string, newStatus: string) => {
    try {
      await updateApplicationStatus(appId, newStatus);
      await fetchApps();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to update status");
    }
  };

  const handleDelete = async (appId: string) => {
    if (!confirm("Remove this application?")) return;
    try {
      await deleteApplication(appId);
      await fetchApps();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to delete");
    }
  };

  const grouped = KANBAN_COLUMNS.reduce(
    (acc, status) => {
      acc[status] = apps.filter((a) => a.status === status);
      return acc;
    },
    {} as Record<string, ApplicationResponse[]>,
  );

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Applications</h1>
          <p className="text-muted-foreground">
            Track your job applications through every stage.
          </p>
        </div>
        <Badge variant="secondary" className="text-sm">
          {apps.length} total
        </Badge>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap gap-2">
        <Button
          variant={activeFilter === null ? "default" : "outline"}
          size="sm"
          onClick={() => setActiveFilter(null)}
        >
          All
        </Button>
        {KANBAN_COLUMNS.map((status) => {
          const config = STATUS_CONFIG[status];
          return (
            <Button
              key={status}
              variant={activeFilter === status ? "default" : "outline"}
              size="sm"
              onClick={() => setActiveFilter(status)}
            >
              {config.icon} {config.label}
            </Button>
          );
        })}
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex items-center justify-center py-12">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        </div>
      ) : error ? (
        <Card>
          <CardContent className="py-8 text-center">
            <p className="text-destructive">{error}</p>
            <Button variant="outline" className="mt-4" onClick={fetchApps}>
              Retry
            </Button>
          </CardContent>
        </Card>
      ) : apps.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
            <span className="text-5xl">📋</span>
            <div>
              <h3 className="text-lg font-semibold">No applications yet</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                Save a job from Career Radar to start tracking your applications.
              </p>
            </div>
          </CardContent>
        </Card>
      ) : (
        /* Kanban board */
        <div className="grid gap-4 lg:grid-cols-5">
          {KANBAN_COLUMNS.map((status) => {
            const config = STATUS_CONFIG[status];
            const columnApps = grouped[status] || [];
            return (
              <div key={status} className="space-y-3">
                {/* Column header */}
                <div className="flex items-center gap-2">
                  <span>{config.icon}</span>
                  <h3 className="text-sm font-semibold">{config.label}</h3>
                  <Badge variant="secondary" className="ml-auto text-xs">
                    {columnApps.length}
                  </Badge>
                </div>

                {/* Cards */}
                <div className="space-y-2">
                  {columnApps.map((app) => (
                    <Card
                      key={app.id}
                      className="transition-all duration-150 hover:shadow-md"
                    >
                      <CardHeader className="p-3 pb-1">
                        <CardTitle className="text-sm leading-tight">
                          {app.job_title || "Untitled Job"}
                        </CardTitle>
                        <CardDescription className="text-xs">
                          {app.job_company || "Unknown Company"}
                        </CardDescription>
                      </CardHeader>
                      <CardContent className="p-3 pt-0">
                        <p className="mb-2 text-xs text-muted-foreground">
                          {new Date(app.created_at).toLocaleDateString()}
                        </p>

                        {/* Quick actions */}
                        <div className="flex flex-wrap gap-1">
                          {status === "saved" && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-6 text-xs"
                              onClick={() =>
                                handleStatusUpdate(app.id, "applied")
                              }
                            >
                              📨 Apply
                            </Button>
                          )}
                          {status === "applied" && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="h-6 text-xs"
                              onClick={() =>
                                handleStatusUpdate(app.id, "interviewing")
                              }
                            >
                              🎤 Interview
                            </Button>
                          )}
                          {status === "interviewing" && (
                            <>
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-6 text-xs"
                                onClick={() =>
                                  handleStatusUpdate(app.id, "offered")
                                }
                              >
                                🎉 Offer
                              </Button>
                              <Button
                                variant="outline"
                                size="sm"
                                className="h-6 text-xs"
                                onClick={() =>
                                  handleStatusUpdate(app.id, "rejected")
                                }
                              >
                                ✖ Reject
                              </Button>
                            </>
                          )}
                          {["saved", "applied", "interviewing"].includes(
                            status,
                          ) && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-6 text-xs text-muted-foreground"
                              onClick={() => handleDelete(app.id)}
                            >
                              🗑
                            </Button>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                  {columnApps.length === 0 && (
                    <div className="rounded-lg border border-dashed p-4 text-center text-xs text-muted-foreground">
                      No {config.label.toLowerCase()} applications
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
