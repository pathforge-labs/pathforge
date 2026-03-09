"use client";

import { useState, type ReactElement } from "react";
import Link from "next/link";
import { Check } from "lucide-react";
import { LANDING_TIERS } from "@/data/landing-data";

/** Monthly/Annual toggle + 3 pricing cards with glassmorphism design */
export function PricingCards(): ReactElement {
  const [isAnnual, setIsAnnual] = useState(false);

  return (
    <div className="mx-auto max-w-5xl">
      {/* ── Billing Toggle ─────────────────────────── */}
      <div className="mb-12 flex items-center justify-center gap-3">
        <span
          className={`text-sm font-medium transition-colors ${
            !isAnnual ? "text-foreground" : "text-muted-foreground"
          }`}
        >
          Monthly
        </span>
        <button
          type="button"
          role="switch"
          aria-checked={isAnnual}
          aria-label="Toggle annual billing"
          onClick={() => setIsAnnual((previous) => !previous)}
          className="pricing-toggle-track group relative inline-flex h-8 w-14 shrink-0 cursor-pointer items-center rounded-full transition-colors duration-300"
        >
          <span
            className={`pointer-events-none block h-5.5 w-5.5 rounded-full shadow-lg ring-1 ring-black/5 transition-all duration-300 ${
              isAnnual
                ? "translate-x-[30px] bg-white"
                : "translate-x-[4px] bg-white"
            }`}
          />
        </button>
        <span
          className={`text-sm font-medium transition-colors ${
            isAnnual ? "text-foreground" : "text-muted-foreground"
          }`}
        >
          Annual
        </span>
        {isAnnual && (
          <span className="pricing-savings-badge ml-1 rounded-full bg-emerald-500/15 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
            Save up to 36%
          </span>
        )}
      </div>

      {/* ── Tier Cards ─────────────────────────────── */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {LANDING_TIERS.map((tier) => {
          const TierIcon = tier.icon;
          return (
            <div
              key={tier.name}
              className={`pricing-card group relative flex cursor-pointer flex-col rounded-2xl p-6 transition-all duration-300 ${
                tier.popular
                  ? "pricing-card-popular pt-8"
                  : "pricing-card-standard"
              }`}
            >
              {/* Popular badge */}
              {tier.popular && (
                <div className="absolute -top-3.5 left-1/2 z-10 -translate-x-1/2">
                  <span className="whitespace-nowrap rounded-full bg-linear-to-r from-violet-500 to-purple-500 px-4 py-1.5 text-xs font-bold text-white shadow-lg shadow-violet-500/25">
                    Most Popular
                  </span>
                </div>
              )}

              {/* Header */}
              <div className="mb-6">
                <div className="mb-3 flex items-center gap-3">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-xl bg-linear-to-br ${tier.gradient} p-2`}
                  >
                    <TierIcon className="h-5 w-5 text-white" />
                  </div>
                  <h3 className="font-display text-xl font-bold">{tier.name}</h3>
                </div>
                <p className="text-sm text-muted-foreground">{tier.description}</p>
              </div>

              {/* Price */}
              <div className="mb-6">
                <div className="flex items-baseline gap-1">
                  <span className="pricing-price font-display text-4xl font-bold tracking-tight">
                    {isAnnual && tier.annualPriceDisplay !== "€0"
                      ? tier.annualPriceDisplay
                      : tier.price}
                  </span>
                  <span className="text-sm text-foreground/60">
                    {isAnnual && tier.annualPriceDisplay !== "€0"
                      ? "/yr"
                      : tier.period}
                  </span>
                </div>
                {isAnnual && tier.annualSavings && (
                  <p className="mt-1 text-xs font-medium text-emerald-400">
                    {tier.annualSavings}
                  </p>
                )}
              </div>

              {/* Features */}
              <ul className="mb-8 flex-1 space-y-3">
                {tier.features.map((feature) => (
                  <li key={feature} className="flex items-start gap-2.5 text-sm">
                    <Check
                      className={`mt-0.5 h-4 w-4 shrink-0 ${
                        tier.popular ? "text-primary" : "text-emerald-400"
                      }`}
                    />
                    <span className="text-foreground/70">{feature}</span>
                  </li>
                ))}
              </ul>

              {/* CTA */}
              <Link
                href="/#waitlist"
                className={`inline-flex w-full cursor-pointer items-center justify-center rounded-xl px-6 py-3 text-sm font-semibold transition-all duration-300 ${
                  tier.popular
                    ? "bg-primary text-primary-foreground shadow-lg shadow-primary/25 hover:shadow-xl hover:shadow-primary/30 hover:brightness-110"
                    : "border border-border bg-card/80 text-foreground hover:border-primary/40 hover:bg-primary/10"
                }`}
              >
                {tier.cta}
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
