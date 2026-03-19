# Runbook: Redis Outage

> **Severity**: P1 — Auth degradation, rate limiting bypass
> **Owner**: Backend / Infra
> **Last Updated**: 2026-03-19

## Symptoms

- `/api/v1/health/ready` returns 503 with `"rate_limiting": "degraded (memory://)"`
- Sentry alerts: `CRITICAL` log — "Redis connection failed, falling back to memory://"
- Security log: `"Token blacklist check failed"` messages
- Rate limiting not enforced consistently across instances

## Impact

| Component | Impact |
|---|---|
| Token Blacklist | Fail-closed (503 for all auth) if `token_blacklist_fail_mode=closed`; fail-open (revoked tokens accepted) if `open` |
| Rate Limiting | Falls back to in-memory — per-instance limits (effectively doubled with 2 instances) |
| Circuit Breaker | State lost — all circuits reset to CLOSED (allows all requests) |
| LLM Budget | Budget tracking lost — monthly spend guard ineffective until Redis recovers |

## Diagnosis

```bash
# Check Railway Redis service status
railway logs --service redis

# Test Redis connectivity from API
curl https://api.pathforge.eu/api/v1/health/ready | jq '.redis'

# Check Redis memory usage (if accessible)
redis-cli -u $REDIS_URL INFO memory
```

## Resolution

### 1. Verify Redis Service Health

```bash
# Railway: check if Redis addon is running
railway status

# If Redis crashed, restart it
railway restart --service redis
```

### 2. If Redis is permanently down

- **Provision new Redis**: Railway plugin or Upstash free tier
- Update `REDIS_URL` and `RATELIMIT_STORAGE_URI` in Railway env vars
- Redeploy API to pick up new connection

### 3. Monitor Recovery

```bash
# Verify health check returns healthy
curl https://api.pathforge.eu/api/v1/health/ready | jq '.status'
# Expected: "ok"

# Verify rate limiting is no longer degraded
curl https://api.pathforge.eu/api/v1/health/ready | jq '.rate_limiting'
# Expected: "ok"
```

## Prevention

- Set up UptimeRobot alert on `/api/v1/health/ready` (Sprint 41)
- Configure Sentry alert rule for `CRITICAL` log level
- Railway auto-restart should handle transient Redis crashes
