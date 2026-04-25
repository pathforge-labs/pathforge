/**
 * PathForge — BillingStatusCard Component
 * ==========================================
 * Displays current subscription status, plan details, and usage.
 *
 * Shows: tier badge, billing period, renewal date, usage progress,
 * and manage subscription button.
 */

"use client";

import { useSubscription, useUsage, useCreatePortal } from "@/hooks/api/use-billing";

interface BillingStatusCardProps {
  readonly className?: string;
}

export function BillingStatusCard({ className = "" }: BillingStatusCardProps) {
  const { data: subscription, isLoading: subLoading } = useSubscription();
  const { data: usage, isLoading: usageLoading } = useUsage();
  const portal = useCreatePortal();

  const isLoading = subLoading || usageLoading;

  if (isLoading) {
    return (
      <div className={`billing-status ${className}`} aria-busy="true">
        <div className="billing-status__skeleton" aria-label="Loading billing status">
          <div className="billing-status__skeleton-line" />
          <div className="billing-status__skeleton-line billing-status__skeleton-line--short" />
          <div className="billing-status__skeleton-bar" />
        </div>
      </div>
    );
  }

  if (!subscription) return null;

  const isFree = subscription.tier === "free";
  const usagePercent = usage && usage.scans_limit > 0
    ? Math.min(100, Math.round((usage.scans_used / usage.scans_limit) * 100))
    : 0;
  const isUnlimited = usage?.scans_limit === 0 || subscription.tier === "premium";

  return (
    <div className={`billing-status ${className}`} role="region" aria-label="Billing status">
      <div className="billing-status__header">
        <h3 className="billing-status__title">Current Plan</h3>
        <span className={`billing-status__badge billing-status__badge--${subscription.tier}`}>
          {subscription.tier.charAt(0).toUpperCase() + subscription.tier.slice(1)}
        </span>
      </div>

      {/* Status */}
      <div className="billing-status__info">
        <div className="billing-status__row">
          <span className="billing-status__label">Status</span>
          <span className={`billing-status__value billing-status__value--${subscription.status}`}>
            {subscription.status.charAt(0).toUpperCase() + subscription.status.slice(1).replace("_", " ")}
          </span>
        </div>

        {subscription.current_period_end && (
          <div className="billing-status__row">
            <span className="billing-status__label">
              {subscription.cancel_at_period_end ? "Access until" : "Renews on"}
            </span>
            <span className="billing-status__value">
              {new Date(subscription.current_period_end).toLocaleDateString("en-GB", {
                day: "numeric",
                month: "long",
                year: "numeric",
              })}
            </span>
          </div>
        )}

        {subscription.cancel_at_period_end && (
          <p className="billing-status__cancel-notice" role="alert">
            Your subscription will not renew. You&apos;ll retain access until the end of your current period.
          </p>
        )}
      </div>

      {/* Usage */}
      {usage && (
        <div className="billing-status__usage" aria-label="Scan usage">
          <div className="billing-status__row">
            <span className="billing-status__label">Scans this period</span>
            <span className="billing-status__value">
              {usage.scans_used} / {isUnlimited ? "∞" : usage.scans_limit}
            </span>
          </div>
          {!isUnlimited && (
            <div
              className="billing-status__progress"
              role="progressbar"
              aria-valuenow={usagePercent}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-label={`${usagePercent}% of scan limit used`}
            >
              <div
                className={`billing-status__progress-bar ${usagePercent >= 90 ? "billing-status__progress-bar--warning" : ""}`}
                style={{ width: `${usagePercent}%` }}
              />
            </div>
          )}
        </div>
      )}

      {/* Actions */}
      <div className="billing-status__actions">
        {!isFree && (
          <button
            type="button"
            className="billing-status__manage-btn"
            onClick={() => portal.mutate()}
            disabled={portal.isPending}
            aria-busy={portal.isPending}
          >
            {portal.isPending ? "Opening portal…" : "Manage Subscription"}
          </button>
        )}
        {isFree && (
          <a href="/pricing" className="billing-status__upgrade-link">
            Upgrade Plan
          </a>
        )}
      </div>
    </div>
  );
}
