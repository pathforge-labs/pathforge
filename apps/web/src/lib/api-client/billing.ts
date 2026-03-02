/**
 * PathForge — API Client: Billing
 * ==================================
 * Stripe billing domain endpoints.
 *
 * Uses fetchWithAuth for authenticated endpoints (subscription, usage,
 * checkout, portal) and fetchPublic for unauthenticated access to the
 * features endpoint (pricing page needs this without auth — AC6).
 */

import { fetchPublic, fetchWithAuth, post } from "@/lib/http";
import type {
  CreateCheckoutSessionRequest,
  CreateCheckoutSessionResponse,
  CustomerPortalResponse,
  FeatureAccessResponse,
  SubscriptionResponse,
  UsageSummaryResponse,
} from "@/types/api";

export const billingApi = {
  /** Get current user's subscription details. */
  getSubscription: (): Promise<SubscriptionResponse> =>
    fetchWithAuth<SubscriptionResponse>("/api/v1/billing/subscription"),

  /** Get current billing period usage summary. */
  getUsage: (): Promise<UsageSummaryResponse> =>
    fetchWithAuth<UsageSummaryResponse>("/api/v1/billing/usage"),

  /**
   * Get feature access for the current user.
   * Uses fetchPublic when called from unauthenticated contexts (pricing page).
   */
  getFeatures: (): Promise<FeatureAccessResponse> =>
    fetchWithAuth<FeatureAccessResponse>("/api/v1/billing/features"),

  /**
   * Get feature access without authentication (pricing page — AC6).
   * Returns default free-tier features when no user is authenticated.
   */
  getFeaturesPublic: (): Promise<FeatureAccessResponse> =>
    fetchPublic<FeatureAccessResponse>("/api/v1/billing/features"),

  /** Create a Stripe Checkout session for upgrading. */
  createCheckout: (
    data: CreateCheckoutSessionRequest,
  ): Promise<CreateCheckoutSessionResponse> =>
    post<CreateCheckoutSessionResponse>("/api/v1/billing/checkout", data),

  /** Create a Stripe Customer Portal session for managing subscription. */
  createPortal: (): Promise<CustomerPortalResponse> =>
    post<CustomerPortalResponse>("/api/v1/billing/portal"),
};
