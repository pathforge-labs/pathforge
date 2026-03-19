# Runbook: DDoS / High Traffic

> **Severity**: P1 — Service degradation or outage
> **Owner**: Backend / Infra
> **Last Updated**: 2026-03-19

## Symptoms

- Elevated 429 (Too Many Requests) responses in logs
- API response times spike above 5 seconds
- Railway metrics show CPU/memory saturation
- Cloudflare Turnstile challenges increase
- Health check intermittently fails

## Impact

Legitimate users may experience slow responses, timeouts, or 429 errors. In extreme cases, the API becomes unreachable.

## Defense Layers

| Layer | Mechanism | Config |
|---|---|---|
| Edge | Cloudflare (via Vercel/Railway) | Automatic DDoS mitigation |
| Application | SlowAPI rate limiting | Per-user/IP limits |
| Registration | Cloudflare Turnstile CAPTCHA | Bot prevention |
| Honeypot | BotTrapMiddleware | Scanner traps (/.env, /wp-admin) |
| LLM | Budget guard + RPM limits | Cost protection |

## Diagnosis

```bash
# Check rate limit status
curl https://api.pathforge.eu/api/v1/health/ready | jq '.rate_limiting'

# Check Railway resource usage
railway logs --service api | tail -100

# Look for bot trap hits (production only)
railway logs --service api | grep "Bot trap"
```

## Resolution

### 1. If Rate Limiting is Degraded (memory://)

Rate limits are per-instance when Redis is down. Fix Redis first (see `redis-outage.md`).

### 2. Tighten Rate Limits

```bash
# Reduce global rate limit temporarily
railway variables set RATE_LIMIT_GLOBAL_DEFAULT="50/minute"
railway restart --service api
```

### 3. Block Specific IPs (if identifiable)

Use Railway's or Cloudflare's IP blocking if attack source is identifiable. PathForge doesn't have its own IP blocklist — rely on infrastructure-level blocking.

### 4. Scale Up

Railway auto-scales but may need manual intervention:
- Railway Dashboard → Service → Settings → Scale
- Increase min/max instances

### 5. Enable Maintenance Mode (last resort)

If the API is completely overwhelmed, disable non-essential features:

```bash
# Disable billing (reduces webhook processing)
railway variables set BILLING_ENABLED=false

# Disable LLM features (reduces external API calls)
railway variables set LLM_MONTHLY_BUDGET_USD=0

railway restart --service api
```

## Prevention

- UptimeRobot monitors for early detection (Sprint 41)
- Sentry alerts on elevated error rates
- Rate limiting covers all endpoints with per-user identification
- Bot trap catches common scanner patterns
- Turnstile prevents automated registration abuse
