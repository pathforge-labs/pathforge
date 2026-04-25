/**
 * PathForge — GuestGuard
 * ========================
 * Prevents authenticated users from accessing guest-only pages
 * (e.g., login, register). Redirects to dashboard.
 */

"use client";

import { useRouter } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/hooks/use-auth";

interface GuestGuardProps {
  children: ReactNode;
  /** Where to redirect authenticated users. Defaults to `/dashboard`. */
  dashboardPath?: string;
}

export function GuestGuard({
  children,
  dashboardPath = "/dashboard",
}: GuestGuardProps): React.JSX.Element | null {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && isAuthenticated) {
      router.replace(dashboardPath);
    }
  }, [isLoading, isAuthenticated, router, dashboardPath]);

  // Show nothing while restoring session or redirecting
  if (isLoading || isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
