/**
 * PathForge — API Types: Billing
 * ================================
 * TypeScript interfaces mirroring backend Pydantic schemas
 * for the Stripe billing domain (Sprint 34–35).
 */

// ── Enums ──────────────────────────────────────────────────

export type SubscriptionTier = "free" | "pro" | "premium";

export type SubscriptionStatus =
  | "active"
  | "trialing"
  | "past_due"
  | "canceled"
  | "unpaid"
  | "incomplete";

// ── Responses ──────────────────────────────────────────────

export interface SubscriptionResponse {
  readonly id: string;
  readonly user_id: string;
  readonly tier: SubscriptionTier;
  readonly status: SubscriptionStatus;
  readonly stripe_customer_id: string | null;
  readonly stripe_subscription_id: string | null;
  readonly current_period_start: string | null;
  readonly current_period_end: string | null;
  readonly cancel_at_period_end: boolean;
  readonly created_at: string;
  readonly updated_at: string;
}

export interface UsageSummaryResponse {
  readonly tier: SubscriptionTier;
  readonly scans_used: number;
  readonly scans_limit: number;
  readonly period_start: string;
  readonly period_end: string;
}

export interface FeatureAccessResponse {
  readonly tier: SubscriptionTier;
  readonly engines: ReadonlyArray<string>;
  readonly scan_limit: number;
  readonly billing_enabled: boolean;
}

export interface BillingEventResponse {
  readonly id: string;
  readonly event_type: string;
  readonly stripe_event_id: string | null;
  readonly data: Record<string, unknown>;
  readonly created_at: string;
}

// ── Requests / Mutations ───────────────────────────────────

export interface CreateCheckoutSessionRequest {
  readonly tier: "pro" | "premium";
  readonly annual?: boolean;
  readonly success_url: string;
  readonly cancel_url: string;
}

export interface CreateCheckoutSessionResponse {
  readonly checkout_url: string;
}

export interface CustomerPortalResponse {
  readonly portal_url: string;
}
