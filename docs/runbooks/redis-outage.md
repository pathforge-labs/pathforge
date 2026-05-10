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

---

## Post-issue-#49 addendum (2026-05-09): regression recovery on Railway

A specific failure mode observed during the issue #49 deploy chain
that the symptoms above do not directly cover, with a confirmed
recovery path:

### Symptom

- `/api/v1/health/ready` returns 503 with
  `"redis":"error", "redis_detail":{"scheme":"rediss",…}` —
  **`scheme: rediss` is the smoking gun** when running against
  the Railway-internal Redis service. The ADR-0002 corrigendum
  (PR #70) requires `scheme: redis` (plaintext) on
  `*.railway.internal` hostnames, so a `rediss://` scheme means
  the container is somehow not running the bypass code path.
- Container `uptime_seconds` larger than the time since the last
  successful deploy run (the container has been auto-restarted
  by Railway, not redeployed by us).
- Live API `version` matches what we expect from `git log`, so
  the regression is not a stale code branch — it's a stale
  image / stale env-var state on Railway's side.

### Root cause class

Railway's container auto-restart (triggered by Redis hiccup,
healthcheck failure, sleep/wake cycles) can resurrect a container
from a cached image that does not match the most recently built
deploy. Symptoms mimic "code regression" without the code actually
having regressed. Same applies to dashboard "Restart" and the
default "Redeploy" button — both reuse the cached image.

### Recovery — DO NOT use Railway dashboard buttons

| Action | Result |
|---|---|
| Dashboard → service → Restart | Reuses cached image. May not pick up env var changes or fix stale-image regression. |
| Dashboard → deployment → Redeploy (default) | Same — re-runs the same image. |
| **`gh workflow run deploy.yml --ref main -f confirm=deploy`** | **Forces a fresh `railway up`: re-uploads source, rebuilds image, re-resolves env reference variables. This is the only path that reliably clears the regression.** |

```bash
# Trigger a fresh build + deploy
gh workflow run deploy.yml --ref main -f confirm=deploy

# Watch the run (5–7 minutes typical)
gh run list --workflow=deploy --limit 1
gh run view <run-id> --log | grep -E "trusted internal network|Redis connection pool"

# Verify recovery
curl https://api.pathforge.eu/api/v1/health/ready | jq '.redis_detail.scheme'
# Expected: "redis"  (NOT "rediss")
curl https://api.pathforge.eu/api/v1/health/ready | jq '.redis'
# Expected: "connected"
```

### Why workflow_dispatch and not dashboard?

`railway up` (which `deploy.yml` runs) uploads the local source
tree fresh and builds a new image. Railway's dashboard buttons
re-deploy an existing image. When the symptom is "container booted
from a cached image that doesn't match production HEAD," only a
fresh build resolves it.

If the regression repeats more than once a week, escalate to a
defensive in-app fix: add Redis connection-pool reconnect logic so
a transient Redis outage doesn't leave the pool in a permanently
unhealthy state. Until that frequency is observed, the
`workflow_dispatch` recovery is the sufficient response.
