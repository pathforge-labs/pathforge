/**
 * PathForge — PricingPageClient
 * ================================
 * Client component for the pricing page interactive elements.
 *
 * Handles billing_enabled state (AC3/ADR-035-11):
 * - billing_enabled=true → show checkout CTAs
 * - billing_enabled=false → show "Coming Soon" badges
 *
 * Uses fetchPublic for unauthenticated access (AC6).
 */

"use client";

import { useQuery } from "@tanstack/react-query";

import { billingApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import type { FeatureAccessResponse } from "@/types/api";

import { PricingGrid } from "@/components/billing/PricingGrid";

export function PricingPageClient() {
  // Use public endpoint — no auth required for pricing page (AC6)
  const { data: features } = useQuery<FeatureAccessResponse>({
    queryKey: queryKeys.billing.features(),
    queryFn: () => billingApi.getFeaturesPublic(),
    staleTime: 300_000,
    gcTime: 600_000,
    retry: 1,
  });

  // AC3: graceful degradation — default to disabled until confirmed
  const billingEnabled = features?.billing_enabled ?? false;

  return <PricingGrid billingEnabled={billingEnabled} />;
}
