/**
 * PathForge — Root Providers
 * ===========================
 * Client-side provider composition for the app root.
 *
 * Wraps: QueryProvider → AuthProvider → children
 * Used by the Server Component root layout to inject client providers.
 */

"use client";

import type { ReactNode } from "react";

import { AuthProvider } from "@/providers/auth-provider";
import { QueryProvider } from "@/providers/query-provider";

interface ProvidersProps {
  children: ReactNode;
}

export function Providers({ children }: ProvidersProps): React.JSX.Element {
  return (
    <QueryProvider>
      <AuthProvider>{children}</AuthProvider>
    </QueryProvider>
  );
}
