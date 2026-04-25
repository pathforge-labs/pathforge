# Runbook: Database Connection Exhaustion

> **Severity**: P0 — Total API failure
> **Owner**: Backend / Infra
> **Last Updated**: 2026-03-19

## Symptoms

- `/api/v1/health/ready` returns 503 with `"database": "error: ..."`
- API returns 500 errors on all authenticated endpoints
- Sentry: `TimeoutError` or `QueuePool limit` exceptions
- Slow response times → cascading timeouts

## Impact

All API endpoints that require database access will fail. Health check returns 503, Railway may restart the service.

## Current Pool Configuration

```python
# config.py / database.py
pool_size = 20          # Base connections
max_overflow = 10       # Burst connections (total max: 30)
pool_pre_ping = True    # Detect stale connections
pool_recycle = 3600     # Recycle after 1 hour
pool_timeout = 30       # Wait max 30s for connection
```

## Diagnosis

```bash
# Check API health
curl https://api.pathforge.eu/api/v1/health/ready | jq '.'

# Check Supabase connection count (via Supabase dashboard)
# Navigate to: Settings → Database → Connection Pooling

# Check Railway API logs for pool errors
railway logs --service api | grep -i "pool\|connection\|timeout"
```

## Resolution

### 1. Check for Long-Running Queries

```sql
-- Run in Supabase SQL Editor
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '5 minutes'
  AND state != 'idle';
```

### 2. Kill Stuck Connections (if needed)

```sql
-- Kill connections older than 10 minutes
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE (now() - pg_stat_activity.query_start) > interval '10 minutes'
  AND state != 'idle'
  AND pid != pg_backend_pid();
```

### 3. Restart API Service

```bash
# Railway restart picks up fresh connection pool
railway restart --service api

# Verify recovery
curl https://api.pathforge.eu/api/v1/health/ready | jq '.database'
# Expected: "connected"
```

### 4. If Supabase is Down

Check [Supabase Status](https://status.supabase.com/). If Supabase is experiencing an outage, the API will return 503 until service is restored. No action possible on our side.

## Prevention

- Monitor connection count via Supabase dashboard
- `pool_pre_ping=True` auto-detects stale connections
- `pool_recycle=3600` prevents connection timeouts
- Consider increasing `pool_size` if traffic exceeds 20 concurrent DB sessions
