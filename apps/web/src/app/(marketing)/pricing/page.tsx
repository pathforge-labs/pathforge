/**
 * PathForge — Pricing Page
 * ==========================
 * Sprint 35: Public marketing page for plan comparison and checkout initiation.
 *
 * Architecture: ADR-035-04 — pricing page is a marketing route (no auth required).
 * AC3/ADR-035-11: graceful degradation when billing_enabled=false.
 * FA2: JSON-LD Product structured data for Google rich results.
 */

import type { Metadata } from "next";

import { APP_NAME, APP_URL } from "@/config/brand";
import { PRICING_TIERS } from "@/config/pricing";

import { PricingPageClient } from "./PricingPageClient";

// ── Metadata ───────────────────────────────────────────────

export const metadata: Metadata = {
  title: "Pricing",
  description: `Compare ${APP_NAME} plans. Start free, upgrade to Pro or Premium for advanced career intelligence. Cancel anytime.`,
  openGraph: {
    title: `${APP_NAME} Pricing — Plans for Every Career Stage`,
    description: `From free to premium — find the ${APP_NAME} plan that matches your career ambitions.`,
    url: `${APP_URL}/pricing`,
    type: "website",
  },
};

// ── JSON-LD Structured Data (FA2) ──────────────────────────

function generateJsonLd(): object {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: `${APP_NAME} Pricing`,
    description: `Compare ${APP_NAME} career intelligence plans.`,
    url: `${APP_URL}/pricing`,
    mainEntity: PRICING_TIERS.filter((tier) => tier.monthlyPrice > 0).map((tier) => ({
      "@type": "Product",
      name: `${APP_NAME} ${tier.name}`,
      description: tier.features.join(", "),
      offers: {
        "@type": "Offer",
        price: tier.monthlyPrice,
        priceCurrency: "EUR",
        priceValidUntil: new Date(Date.now() + 365 * 24 * 60 * 60 * 1000).toISOString().split("T")[0],
        availability: "https://schema.org/InStock",
      },
    })),
  };
}

// ── Page Component ─────────────────────────────────────────

export default function PricingPage() {
  const jsonLd = generateJsonLd();

  return (
    <>
      {/* JSON-LD for SEO */}
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />

      <div className="pricing-page">
        <header className="pricing-page__header">
          <h1 className="pricing-page__title">
            Simple, Transparent Pricing
          </h1>
          <p className="pricing-page__subtitle">
            Start free. Upgrade when you&apos;re ready. Cancel anytime.
          </p>
        </header>

        {/* Client component handles billing state and interactions */}
        <PricingPageClient />

        <section className="pricing-page__faq" aria-label="Frequently asked questions">
          <h2>Frequently Asked Questions</h2>
          <dl className="pricing-page__faq-list">
            <div className="pricing-page__faq-item">
              <dt>Can I change plans later?</dt>
              <dd>Yes — upgrade, downgrade, or cancel anytime from your billing settings.</dd>
            </div>
            <div className="pricing-page__faq-item">
              <dt>What payment methods do you accept?</dt>
              <dd>We accept all major credit and debit cards via Stripe. Payments are processed securely.</dd>
            </div>
            <div className="pricing-page__faq-item">
              <dt>Is there a free trial?</dt>
              <dd>The Free plan is always free with {PRICING_TIERS[0].scanLimit} scans per month. No credit card required.</dd>
            </div>
            <div className="pricing-page__faq-item">
              <dt>What happens when I reach my scan limit?</dt>
              <dd>You&apos;ll be prompted to upgrade. Your data is always safe and accessible.</dd>
            </div>
          </dl>
        </section>
      </div>
    </>
  );
}
