/**
 * PathForge — Billing Settings Page
 * =====================================
 * Sprint 35: Dashboard settings sub-route for billing management.
 *
 * Architecture: ADR-035-03 — billing as settings sub-route (not top-level sidebar).
 * R2: Checkout return handler with query param parsing and toast feedback.
 */

"use client";

import { useEffect } from "react";
import { useSearchParams } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { queryKeys } from "@/lib/query-keys";
import { BillingStatusCard } from "@/components/billing/BillingStatusCard";
import { UpgradeBanner } from "@/components/billing/UpgradeBanner";
import { useSubscription } from "@/hooks/api/use-billing";

export default function BillingPage() {
  const searchParams = useSearchParams();
  const queryClient = useQueryClient();
  const { data: subscription } = useSubscription();

  // R2: Checkout return handler — process ?checkout=success|canceled
  useEffect(() => {
    const checkoutStatus = searchParams.get("checkout");

    if (checkoutStatus === "success") {
      // Invalidate billing queries to refresh subscription state
      void queryClient.invalidateQueries({ queryKey: queryKeys.billing.all });

      // Dynamic import to avoid bundle cost when not needed (D2)
      void import("sonner").then(({ toast }) => {
        toast.success("Subscription activated!", {
          description: "Your plan has been upgraded successfully. Welcome to your new tier!",
          duration: 6000,
        });
      });
    } else if (checkoutStatus === "canceled") {
      void import("sonner").then(({ toast }) => {
        toast.info("Checkout canceled", {
          description: "No changes were made to your subscription.",
          duration: 4000,
        });
      });
    }
  }, [searchParams, queryClient]);

  return (
    <div className="billing-page">
      <header className="billing-page__header">
        <h2 className="billing-page__title">Billing & Subscription</h2>
        <p className="billing-page__description">
          Manage your subscription, view usage, and update billing preferences.
        </p>
      </header>

      {/* Current Plan Status */}
      <BillingStatusCard className="billing-page__status" />

      {/* Upgrade Banner — only for free-tier users */}
      {subscription?.tier === "free" && (
        <UpgradeBanner className="billing-page__upgrade" />
      )}

      {/* Feature Access Overview */}
      <section className="billing-page__section" aria-label="Plan features">
        <h3 className="billing-page__section-title">Your Plan Includes</h3>
        <p className="billing-page__section-description">
          View all available features for your current plan, or{" "}
          <a href="/pricing" className="billing-page__link">compare plans</a>{" "}
          to see what&apos;s available with an upgrade.
        </p>
      </section>
    </div>
  );
}
