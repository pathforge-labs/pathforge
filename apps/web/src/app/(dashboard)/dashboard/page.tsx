"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { healthApi } from "@/lib/api-client/health";
import type { ReadinessCheckResponse } from "@/types/api/health";

export default function DashboardPage() {
  const [apiHealth, setApiHealth] = useState<ReadinessCheckResponse | null>(null);
  const [healthError, setHealthError] = useState<string | null>(null);

  useEffect(() => {
    healthApi
      .ready()
      .then(setApiHealth)
      .catch((err: Error) => setHealthError(err.message));
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Career Dashboard</h1>
        <p className="text-muted-foreground">
          Your Career DNA™ intelligence at a glance.
        </p>
      </div>

      {/* Get Started CTA */}
      <Card className="border-primary/20 bg-gradient-to-br from-primary/5 via-transparent to-primary/5">
        <CardContent className="flex flex-col items-center gap-4 py-8 text-center sm:flex-row sm:text-left">
          <div className="flex h-14 w-14 shrink-0 items-center justify-center rounded-full bg-primary/10">
            <span className="text-3xl">🚀</span>
          </div>
          <div className="flex-1">
            <h3 className="text-lg font-semibold">Get Started with PathForge</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Upload your resume, build your career profile, and discover AI-matched
              job opportunities in minutes.
            </p>
          </div>
          <Link href="/dashboard/onboarding">
            <Button size="lg" className="whitespace-nowrap">
              Start Onboarding →
            </Button>
          </Link>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[
          {
            label: "Career DNA Score",
            value: "—",
            icon: "🧬",
            description: "Upload a resume to begin",
            href: "/dashboard/onboarding",
          },
          {
            label: "Job Matches",
            value: "0",
            icon: "🎯",
            description: "No matches yet",
            href: "/dashboard/matches",
          },
          {
            label: "Resumes",
            value: "0",
            icon: "📄",
            description: "Parse your first resume",
            href: "/dashboard/resumes",
          },
          {
            label: "Threat Level",
            value: "—",
            icon: "🛡️",
            description: "Monitoring inactive",
            href: "/dashboard",
          },
        ].map((stat) => (
          <Link key={stat.label} href={stat.href}>
            <Card className="transition-all duration-200 hover:shadow-md hover:border-primary/20 cursor-pointer">
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">{stat.label}</CardTitle>
                <span className="text-2xl">{stat.icon}</span>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{stat.value}</div>
                <p className="text-xs text-muted-foreground">{stat.description}</p>
              </CardContent>
            </Card>
          </Link>
        ))}
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="mb-3 text-lg font-semibold">Quick Actions</h2>
        <div className="grid gap-3 sm:grid-cols-3">
          <Link href="/dashboard/resumes">
            <Card className="transition-all duration-200 hover:shadow-md hover:border-primary/20 cursor-pointer">
              <CardContent className="flex items-center gap-3 py-4">
                <span className="text-2xl">📄</span>
                <div>
                  <p className="text-sm font-medium">Parse Resume</p>
                  <p className="text-xs text-muted-foreground">Upload and analyze your CV</p>
                </div>
              </CardContent>
            </Card>
          </Link>
          <Link href="/dashboard/matches">
            <Card className="transition-all duration-200 hover:shadow-md hover:border-primary/20 cursor-pointer">
              <CardContent className="flex items-center gap-3 py-4">
                <span className="text-2xl">🎯</span>
                <div>
                  <p className="text-sm font-medium">Career Radar</p>
                  <p className="text-xs text-muted-foreground">View semantic job matches</p>
                </div>
              </CardContent>
            </Card>
          </Link>
          <Link href="/dashboard/onboarding">
            <Card className="transition-all duration-200 hover:shadow-md hover:border-primary/20 cursor-pointer">
              <CardContent className="flex items-center gap-3 py-4">
                <span className="text-2xl">✨</span>
                <div>
                  <p className="text-sm font-medium">Guided Setup</p>
                  <p className="text-xs text-muted-foreground">Complete onboarding wizard</p>
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>

      {/* API Connectivity */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">System Status</CardTitle>
          <CardDescription>Backend API connectivity check</CardDescription>
        </CardHeader>
        <CardContent>
          {apiHealth ? (
            <div className="flex items-center gap-3">
              <Badge variant="default" className="bg-green-600">
                ● Connected
              </Badge>
              <span className="text-sm text-muted-foreground">
                {apiHealth.app} v{apiHealth.version} — Database: {apiHealth.database}
              </span>
            </div>
          ) : healthError ? (
            <div className="flex items-center gap-3">
              <Badge variant="destructive">● Disconnected</Badge>
              <span className="text-sm text-muted-foreground">{healthError}</span>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <Badge variant="secondary">● Checking...</Badge>
              <span className="text-sm text-muted-foreground">
                Connecting to API...
              </span>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
