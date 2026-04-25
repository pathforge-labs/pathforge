# Runbook: Stripe Webhook Failure

> **Severity**: P1 — Billing state desynchronization
> **Owner**: Backend / Billing
> **Last Updated**: 2026-03-19

## Symptoms

- User pays but subscription status doesn't update
- Stripe Dashboard → Webhooks shows failed delivery attempts
- Sentry: `ValueError` or `stripe.error.SignatureVerificationError`
- Billing events missing from `billing_events` table

## Impact

| Scenario | Impact |
|---|---|
| Webhook signature failure | All webhooks rejected — subscriptions never activate |
| Processing error | Individual events lost — user may have wrong tier |
| Endpoint unreachable | Stripe retries for 3 days then gives up |

## Diagnosis

### 1. Check Stripe Webhook Dashboard

Navigate to: [Stripe Dashboard](https://dashboard.stripe.com) → Developers → Webhooks

- Check delivery success rate
- Check recent failed attempts and error messages
- Click on failed event to see request/response details

### 2. Check API Logs

```bash
# Look for webhook-related errors
railway logs --service api | grep -i "webhook\|stripe\|billing"
```

### 3. Common Failures

| Error | Cause | Fix |
|---|---|---|
| `SignatureVerificationError` | Wrong `STRIPE_WEBHOOK_SECRET` | Update env var in Railway |
| `404 Not Found` | Webhook URL misconfigured | Should be `https://api.pathforge.eu/api/v1/webhooks/stripe` |
| `500 Internal Server Error` | Processing bug | Check Sentry for stack trace |
| `429 Too Many Requests` | Rate limit hit | Webhook rate limit is 100/min — investigate burst |

## Resolution

### Signature Verification Failure

```bash
# 1. Get correct webhook secret from Stripe Dashboard → Webhooks → Signing secret
# 2. Update in Railway
railway variables set STRIPE_WEBHOOK_SECRET=whsec_xxx

# 3. Redeploy
railway restart --service api
```

### Resync Missed Events

```bash
# Use Stripe CLI to resend failed events
stripe events resend evt_xxx

# Or manually resend from Stripe Dashboard → Webhooks → Failed attempts → Resend
```

### Kill Switch

If webhooks are causing cascading failures, disable billing:

```bash
railway variables set BILLING_ENABLED=false
railway restart --service api
```

This disables all billing endpoints gracefully. Re-enable after fixing.

## Prevention

- Stripe Dashboard → Webhooks → Configure email alerts for failures
- Idempotent dedup prevents duplicate charges from retried webhooks
- Timestamp ordering rejects stale events
- Monitor `billing_events` table for gaps
