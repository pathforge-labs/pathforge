# PathForge — Performance Baselines

> **Last updated**: 2026-04-23 (Sprint 44 — N-6 prep)
> **Status**: Pending first production run with LLM keys live (OPS-3).
> **Capture command**: `AUTH_TOKEN=<jwt> bash scripts/perf-baseline.sh --api-only`
> **Output**: `docs/baselines/api-<TIMESTAMP>.csv` + `docs/baselines/lighthouse-<TIMESTAMP>/`

---

## API Response Times (p50 / p95, 20 iterations each)

### Infrastructure

| Endpoint                  | p50 | p95 | Threshold p95 | Status  |
| :------------------------ | :-- | :-- | :------------ | :------ |
| `GET /api/v1/health`      | —   | —   | < 50 ms       | Pending |
| `GET /api/v1/health/ready`| —   | —   | < 200 ms      | Pending |

### Intelligence Dashboards (cache-warm — Redis hit path)

| Endpoint                                        | p50 | p95 | Threshold p95 | Status  |
| :---------------------------------------------- | :-- | :-- | :------------ | :------ |
| `GET /api/v1/career-dna`                        | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/career-dna/summary`                | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/career-dna/skills`                 | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/threat-radar`                      | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/threat-radar/signals`              | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/salary-intelligence`               | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/salary-intelligence/estimate`      | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/salary-intelligence/impacts`       | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/salary-intelligence/trajectory`    | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/skill-decay`                       | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/skill-decay/freshness`             | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/skill-decay/market-demand`         | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/skill-decay/velocity`              | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/skill-decay/reskilling`            | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/recommendations/dashboard`         | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/recommendations`                   | —   | —   | < 100 ms      | Pending |
| `GET /api/v1/recommendations/batches`           | —   | —   | < 100 ms      | Pending |

### Intelligence Dashboards (cache-cold — full DB + LLM path)

> Run once after flushing Redis (`FLUSHDB`) to capture cold-path latency.

| Endpoint                          | p50 | p95 | Threshold p95 | Status  |
| :-------------------------------- | :-- | :-- | :------------ | :------ |
| `GET /api/v1/career-dna`         | —   | —   | < 3000 ms     | Pending |
| `GET /api/v1/threat-radar`       | —   | —   | < 3000 ms     | Pending |
| `GET /api/v1/salary-intelligence`| —   | —   | < 3000 ms     | Pending |
| `GET /api/v1/skill-decay`        | —   | —   | < 3000 ms     | Pending |
| `GET /api/v1/recommendations/dashboard` | — | — | < 3000 ms  | Pending |

---

## Web Core Vitals (Lighthouse)

| Page                     | Performance | Accessibility | Best Practices | SEO | Threshold | Status  |
| :----------------------- | :---------- | :------------ | :------------- | :-- | :-------- | :------ |
| Login (`/login`)         | —           | —             | —              | —   | Perf > 70, A11y > 85 | Pending |
| Dashboard (`/dashboard`) | —           | —             | —              | —   | Perf > 70, A11y > 85 | Pending |
| Career DNA (`/dashboard/career-dna`) | — | —          | —              | —   | Perf > 70, A11y > 85 | Pending |

---

## Acceptance Thresholds

| Metric                         | Threshold     | Action on Breach        |
| :----------------------------- | :------------ | :---------------------- |
| API p95 — health               | < 200 ms      | Investigate DB/Redis    |
| API p95 — cached intelligence  | < 100 ms      | Check Redis hit rate    |
| API p95 — cold intelligence    | < 3000 ms     | Warning (LLM latency)   |
| Lighthouse Performance         | > 70          | Block deploy            |
| Lighthouse Accessibility       | > 85          | Block deploy            |

---

## Instructions

**1. Obtain a JWT token:**
```bash
ACCESS_TOKEN=$(curl -s -X POST $API_BASE_URL/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"emre@pathforge.eu","password":"<pw>"}' | jq -r .access_token)
```

**2. Run warm-cache baseline:**
```bash
AUTH_TOKEN=$ACCESS_TOKEN bash scripts/perf-baseline.sh --api-only
```

**3. Flush Redis and run cold-cache baseline:**
```bash
# On Railway shell: redis-cli FLUSHDB
AUTH_TOKEN=$ACCESS_TOKEN bash scripts/perf-baseline.sh --api-only
```

**4. Commit the CSV output:**
```bash
git add docs/baselines/api-*.csv
git commit -m "perf: N-6 baseline capture $(date +%Y-%m-%d)"
```
