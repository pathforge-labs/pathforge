/**
 * PathForge — PricingGrid Component
 * =====================================
 * 3-tier horizontal pricing grid with monthly/annual toggle.
 *
 * Renders all pricing tiers side by side with a billing interval
 * toggle and savings callout on annual plans.
 */

"use client";

import { useState } from "react";

import { PRICING_TIERS } from "@/config/pricing";
import { useCreateCheckout } from "@/hooks/api/use-billing";

import { PricingCard } from "./PricingCard";

interface PricingGridProps {
  readonly billingEnabled: boolean;
}

export function PricingGrid({ billingEnabled }: PricingGridProps) {
  const [isAnnual, setIsAnnual] = useState(false);
  const checkout = useCreateCheckout();

  const handleSelectPlan = (tierId: "pro" | "premium") => {
    checkout.mutate({ tier: tierId, annual: isAnnual });
  };

  return (
    <section className="pricing-grid" aria-label="Pricing plans">
      {/* Billing Interval Toggle */}
      <div className="pricing-grid__toggle" role="radiogroup" aria-label="Billing interval">
        <button
          type="button"
          role="radio"
          aria-checked={!isAnnual}
          className={`pricing-grid__toggle-btn ${!isAnnual ? "pricing-grid__toggle-btn--active" : ""}`}
          onClick={() => setIsAnnual(false)}
        >
          Monthly
        </button>
        <button
          type="button"
          role="radio"
          aria-checked={isAnnual}
          className={`pricing-grid__toggle-btn ${isAnnual ? "pricing-grid__toggle-btn--active" : ""}`}
          onClick={() => setIsAnnual(true)}
        >
          Annual
          <span className="pricing-grid__savings-tag">Save ~17%</span>
        </button>
      </div>

      {/* Tier Cards */}
      <div className="pricing-grid__cards">
        {PRICING_TIERS.map((tier) => (
          <PricingCard
            key={tier.id}
            tier={tier}
            isAnnual={isAnnual}
            billingEnabled={billingEnabled}
            onSelectPlan={handleSelectPlan}
            isLoading={checkout.isPending}
          />
        ))}
      </div>
    </section>
  );
}
