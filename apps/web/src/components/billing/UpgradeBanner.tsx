/**
 * PathForge — UpgradeBanner Component
 * ======================================
 * Contextual banner encouraging free-tier users to upgrade.
 *
 * Shown conditionally when the user is on the free tier.
 * Links to the pricing page for plan comparison.
 */

"use client";

import { useSubscription } from "@/hooks/api/use-billing";

interface UpgradeBannerProps {
  readonly className?: string;
}

export function UpgradeBanner({ className = "" }: UpgradeBannerProps) {
  const { data: subscription, isLoading } = useSubscription();

  // Only show for free-tier users (or when data hasn't loaded yet)
  if (isLoading || !subscription || subscription.tier !== "free") {
    return null;
  }

  return (
    <div className={`upgrade-banner ${className}`} role="complementary" aria-label="Upgrade suggestion">
      <div className="upgrade-banner__content">
        <p className="upgrade-banner__text">
          <strong>Unlock all 12 Intelligence Engines</strong> — upgrade to Pro or Premium for
          advanced career analytics, salary intelligence, and unlimited scans.
        </p>
        <a href="/pricing" className="upgrade-banner__cta">
          View Plans →
        </a>
      </div>
    </div>
  );
}
