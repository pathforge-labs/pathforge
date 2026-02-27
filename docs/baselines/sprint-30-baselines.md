# Sprint 30 — Performance Baselines

> **Captured**: Pending first production deploy with Sprint 30 changes
> **Tools**: Lighthouse CLI, httpx (API P95), Playwright (visual regression)

## API Response Times (P95)

| Endpoint                            | P50 | P95 | P99 | Status  |
| :---------------------------------- | :-- | :-- | :-- | :------ |
| `GET /api/v1/health`                | —   | —   | —   | Pending |
| `GET /api/v1/health/ready`          | —   | —   | —   | Pending |
| `POST /api/v1/auth/login`           | —   | —   | —   | Pending |
| `GET /api/v1/career-dna/summary`    | —   | —   | —   | Pending |
| `GET /api/v1/threat-radar/overview` | —   | —   | —   | Pending |

> Capture command: `bash scripts/perf-baseline.sh`

## Web Core Vitals (Lighthouse)

| Page                     | Performance | Accessibility | Best Practices | SEO | Status  |
| :----------------------- | :---------- | :------------ | :------------- | :-- | :------ |
| Landing (`/`)            | —           | —             | —              | —   | Pending |
| Login (`/login`)         | —           | —             | —              | —   | Pending |
| Dashboard (`/dashboard`) | —           | —             | —              | —   | Pending |

> Capture command: `npx lighthouse <url> --output json --output-path ./docs/baselines/`

## Acceptance Thresholds

| Metric                   | Threshold | Action on Breach |
| :----------------------- | :-------- | :--------------- |
| API P95 (health)         | < 200ms   | Investigate      |
| API P95 (auth)           | < 500ms   | Investigate      |
| API P95 (AI endpoints)   | < 3000ms  | Warning          |
| Lighthouse Performance   | > 70      | Block deploy     |
| Lighthouse Accessibility | > 85      | Block deploy     |

## Visual Regression Baselines

- **Status**: Pending CI pipeline run
- **Tool**: Playwright `toHaveScreenshot()` with 2% tolerance
- **Pages**: Landing, Dashboard, Career DNA, Threat Radar, Command Center, Actions

> [!NOTE]
> Baselines will be populated after the first production deploy of Sprint 30.
> Run `bash scripts/perf-baseline.sh` against production to capture initial values.
