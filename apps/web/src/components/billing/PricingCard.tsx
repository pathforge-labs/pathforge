/**
 * PathForge — PricingCard Component
 * ====================================
 * Individual tier card for the pricing grid.
 *
 * Renders plan details, feature list, price, and CTA.
 * Highlighted variant for the recommended plan (Pro).
 * Accessible: ARIA labels, keyboard navigable, role-based.
 */

"use client";

import { type PricingTier, formatPrice, getAnnualSavingsPercent } from "@/config/pricing";

interface PricingCardProps {
  readonly tier: PricingTier;
  readonly isAnnual: boolean;
  readonly billingEnabled: boolean;
  readonly onSelectPlan: (tierId: "pro" | "premium") => void;
  readonly isLoading?: boolean;
}

export function PricingCard({
  tier,
  isAnnual,
  billingEnabled,
  onSelectPlan,
  isLoading = false,
}: PricingCardProps) {
  const price = isAnnual ? tier.annualPrice : tier.monthlyPrice;
  const period = isAnnual ? "/year" : "/month";
  const savingsPercent = isAnnual ? getAnnualSavingsPercent(tier) : 0;
  const isFree = tier.id === "free";
  const isDisabled = !billingEnabled && !isFree;

  return (
    <div
      role="article"
      aria-label={`${tier.name} plan`}
      className={`pricing-card ${tier.highlighted ? "pricing-card--highlighted" : ""}`}
    >
      {tier.highlighted && (
        <div className="pricing-card__badge" aria-label="Recommended plan">
          Most Popular
        </div>
      )}

      {isDisabled && (
        <div className="pricing-card__badge pricing-card__badge--coming-soon" aria-label="Coming soon">
          Coming Soon
        </div>
      )}

      <div className="pricing-card__header">
        <h3 className="pricing-card__name">{tier.name}</h3>
        <div className="pricing-card__price" aria-label={`${formatPrice(price)} ${isFree ? "" : period}`}>
          <span className="pricing-card__amount">{formatPrice(price)}</span>
          {!isFree && <span className="pricing-card__period">{period}</span>}
        </div>
        {savingsPercent > 0 && (
          <p className="pricing-card__savings" aria-label={`Save ${savingsPercent}% with annual billing`}>
            Save {savingsPercent}% annually
          </p>
        )}
        {tier.scanLimit !== null ? (
          <p className="pricing-card__scans">{tier.scanLimit} scans/month</p>
        ) : (
          <p className="pricing-card__scans pricing-card__scans--unlimited">Unlimited scans</p>
        )}
      </div>

      <ul className="pricing-card__features" role="list">
        {tier.features.map((feature) => (
          <li key={feature} className="pricing-card__feature">
            <span className="pricing-card__feature-icon" aria-hidden="true">
              ✓
            </span>
            {feature}
          </li>
        ))}
      </ul>

      <div className="pricing-card__footer">
        {isFree ? (
          <a
            href="/register"
            className="pricing-card__cta pricing-card__cta--secondary"
            aria-label="Get started with the Free plan"
          >
            {tier.ctaText}
          </a>
        ) : (
          <button
            type="button"
            className={`pricing-card__cta ${tier.highlighted ? "pricing-card__cta--primary" : "pricing-card__cta--secondary"}`}
            onClick={() => onSelectPlan(tier.id as "pro" | "premium")}
            disabled={isDisabled || isLoading}
            aria-label={isDisabled ? `${tier.name} plan coming soon` : `${tier.ctaText}`}
            aria-busy={isLoading}
          >
            {isLoading ? "Redirecting…" : isDisabled ? "Coming Soon" : tier.ctaText}
          </button>
        )}
      </div>
    </div>
  );
}
