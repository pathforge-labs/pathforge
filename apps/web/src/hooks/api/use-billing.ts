/**
 * PathForge — Hook: useBilling
 * ===============================
 * React Query hooks for the Stripe billing domain.
 *
 * Provides: useSubscription, useUsage, useFeatures,
 *           useCreateCheckout, useCreatePortal
 */

"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { billingApi } from "@/lib/api-client";
import { queryKeys } from "@/lib/query-keys";
import { APP_URL } from "@/config/brand";
import type {
  CreateCheckoutSessionResponse,
  CustomerPortalResponse,
  FeatureAccessResponse,
  SubscriptionResponse,
  UsageSummaryResponse,
} from "@/types/api";

// ── Queries ────────────────────────────────────────────────

export function useSubscription() {
  return useQuery<SubscriptionResponse>({
    queryKey: queryKeys.billing.subscription(),
    queryFn: () => billingApi.getSubscription(),
    staleTime: 60_000,
    gcTime: 300_000,
    retry: 1,
  });
}

export function useUsage() {
  return useQuery<UsageSummaryResponse>({
    queryKey: queryKeys.billing.usage(),
    queryFn: () => billingApi.getUsage(),
    staleTime: 60_000,
    gcTime: 300_000,
    retry: 1,
  });
}

export function useFeatures() {
  return useQuery<FeatureAccessResponse>({
    queryKey: queryKeys.billing.features(),
    queryFn: () => billingApi.getFeatures(),
    staleTime: 300_000,
    gcTime: 600_000,
    retry: 1,
  });
}

// ── Mutations ──────────────────────────────────────────────

/**
 * useCreateCheckout — initiates a Stripe Checkout session.
 *
 * On success, redirects the browser to the Stripe-hosted checkout page.
 * Uses APP_URL from brand.ts for success/cancel URLs (I5).
 */
export function useCreateCheckout() {
  const queryClient = useQueryClient();
  const billingPath = "/dashboard/settings/billing";

  return useMutation<CreateCheckoutSessionResponse, Error, { tier: "pro" | "premium"; annual?: boolean }>({
    mutationFn: (variables) =>
      billingApi.createCheckout({
        tier: variables.tier,
        annual: variables.annual ?? false,
        success_url: `${APP_URL}${billingPath}?checkout=success`,
        cancel_url: `${APP_URL}${billingPath}?checkout=canceled`,
      }),
    onSuccess: (data) => {
      // Redirect to Stripe Checkout
      window.location.href = data.checkout_url;
    },
    onSettled: () => {
      // Invalidate billing queries to refresh state on return (R2)
      void queryClient.invalidateQueries({ queryKey: queryKeys.billing.all });
    },
  });
}

/**
 * useCreatePortal — opens the Stripe Customer Portal for subscription management.
 *
 * On success, redirects the browser to the Stripe-hosted portal.
 */
export function useCreatePortal() {
  return useMutation<CustomerPortalResponse, Error, void>({
    mutationFn: () => billingApi.createPortal(),
    onSuccess: (data) => {
      window.location.href = data.portal_url;
    },
  });
}
