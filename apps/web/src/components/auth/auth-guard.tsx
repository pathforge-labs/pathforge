/**
 * PathForge — AuthGuard
 * =======================
 * Client-side route protection component.
 *
 * Wraps protected pages/layouts. Redirects unauthenticated users
 * to the login page while preserving the intended destination.
 */

"use client";

import { useRouter, usePathname } from "next/navigation";
import { useEffect, type ReactNode } from "react";

import { useAuth } from "@/hooks/use-auth";

interface AuthGuardProps {
  children: ReactNode;
  /** Where to redirect unauthenticated users. Defaults to `/login`. */
  loginPath?: string;
}

export function AuthGuard({
  children,
  loginPath = "/login",
}: AuthGuardProps): React.JSX.Element | null {
  const { isAuthenticated, isLoading } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      const returnTo = encodeURIComponent(pathname);
      router.replace(`${loginPath}?returnTo=${returnTo}`);
    }
  }, [isLoading, isAuthenticated, pathname, router, loginPath]);

  // Show nothing while restoring session or redirecting
  if (isLoading || !isAuthenticated) {
    return null;
  }

  return <>{children}</>;
}
