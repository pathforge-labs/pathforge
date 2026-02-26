/**
 * PathForge — Dashboard Layout
 * ==============================
 * Authenticated shell with sidebar navigation, mobile header, and user profile.
 * Uses AuthProvider's useAuth hook for session management (ADR-025-03 migration).
 */

"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/hooks/use-auth";

/* ── Navigation ────────────────────────────────────────────── */

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: "📊" },
  { name: "Onboarding", href: "/dashboard/onboarding", icon: "🚀" },
  { name: "Job Matches", href: "/dashboard/matches", icon: "🎯" },
  { name: "Applications", href: "/dashboard/applications", icon: "📋" },
  { name: "Resumes", href: "/dashboard/resumes", icon: "📄" },
  { name: "Career DNA", href: "/dashboard/career-dna", icon: "🧬" },
  { name: "Threat Radar", href: "/dashboard/threat-radar", icon: "🛡️" },
  { name: "Settings", href: "/dashboard/settings", icon: "⚙️" },
] as const;

/* ── Component ─────────────────────────────────────────────── */

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const pathname = usePathname();
  const { user, isAuthenticated, isLoading, logout } = useAuth();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  // Redirect unauthenticated users to login
  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.push("/login");
    }
  }, [isLoading, isAuthenticated, router]);

  const handleLogout = async (): Promise<void> => {
    await logout();
    router.push("/login");
  };

  if (isLoading || !isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
          <p className="text-sm text-muted-foreground">Loading…</p>
        </div>
      </div>
    );
  }

  const initials = user?.fullName
    ?.split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2) ?? "PF";

  const isActive = (href: string): boolean => {
    if (href === "/dashboard") return pathname === "/dashboard";
    return pathname.startsWith(href);
  };

  return (
    <div className="flex min-h-screen">
      {/* Mobile header */}
      <div className="fixed top-0 left-0 right-0 z-40 flex h-14 items-center justify-between border-b border-border/40 bg-background/95 px-4 backdrop-blur lg:hidden">
        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary">
            <span className="text-xs font-bold text-primary-foreground">P</span>
          </div>
          <span className="text-sm font-bold tracking-tight">PathForge</span>
        </div>
        <Button variant="ghost" size="sm" onClick={() => setSidebarOpen(!sidebarOpen)}>
          {sidebarOpen ? "✕" : "☰"}
        </Button>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 z-40 flex h-full w-64 flex-col border-r border-border/40 bg-sidebar transition-transform duration-200 lg:static lg:translate-x-0 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Brand */}
        <div className="flex h-16 items-center gap-2 px-6">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <span className="text-sm font-bold text-primary-foreground">P</span>
          </div>
          <span className="text-lg font-bold tracking-tight">PathForge</span>
        </div>

        <Separator />

        {/* Navigation */}
        <nav className="flex-1 space-y-1 px-3 py-4">
          {navigation.map((item) => {
            const active = isActive(item.href);
            return (
              <Link
                key={item.name}
                href={item.href}
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-all duration-150 ${
                  active
                    ? "bg-primary/10 text-primary font-medium"
                    : "text-sidebar-foreground hover:bg-sidebar-accent"
                }`}
              >
                <span>{item.icon}</span>
                {item.name}
                {active && (
                  <div className="ml-auto h-1.5 w-1.5 rounded-full bg-primary" />
                )}
              </Link>
            );
          })}
        </nav>

        <Separator />

        {/* User */}
        <div className="flex items-center gap-3 p-4">
          <Avatar className="h-8 w-8">
            <AvatarFallback className="text-xs">{initials}</AvatarFallback>
          </Avatar>
          <div className="flex-1 truncate">
            <p className="truncate text-sm font-medium">{user?.fullName}</p>
            <p className="truncate text-xs text-muted-foreground">{user?.email}</p>
          </div>
          <Button variant="ghost" size="sm" onClick={handleLogout} title="Sign out">
            🚪
          </Button>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto pt-14 lg:pt-0">
        <div className="mx-auto max-w-6xl p-6">{children}</div>
      </main>
    </div>
  );
}
