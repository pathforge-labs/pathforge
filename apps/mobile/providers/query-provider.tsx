/**
 * PathForge Mobile — Query Provider
 * ====================================
 * TanStack Query v5 client with mobile-specific defaults.
 */

import React, { useMemo } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ApiError } from "../lib/http";
import { QUERY_MAX_RETRIES, QUERY_STALE_TIME_MS } from "../constants/config";

interface QueryProviderProps {
  children: React.ReactNode;
}

export function QueryProvider({ children }: QueryProviderProps): React.JSX.Element {
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: QUERY_STALE_TIME_MS,
            retry: (failureCount, error) => {
              // Never retry client errors (4xx)
              if (error instanceof ApiError && !error.isRetryable) {
                return false;
              }
              return failureCount < QUERY_MAX_RETRIES;
            },
            refetchOnWindowFocus: false, // Not applicable on mobile
            refetchOnReconnect: true,
          },
          mutations: {
            retry: false,
          },
        },
      }),
    [],
  );

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}
