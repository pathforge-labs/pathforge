# PathForge — Visual Regression Policy

> Sprint 36 WS-7 | Version 1.0 | Effective: 2026-03-03

## Overview

Visual regression testing ensures that UI changes are intentional and reviewed. Every PR that modifies `apps/web/**` triggers a visual regression CI job that compares full-page screenshots against committed baselines.

## Baseline Management

### Capture Environment

- **Baselines MUST be captured in CI** (Ubuntu runner with Chromium)
- Local screenshots are for development debugging only — **never commit** local baselines
- Font rendering, anti-aliasing, and subpixel hinting differ across macOS, Windows, and Linux

### Creating Baselines

First-time or intentional updates:

1. Run the `visual-regression` workflow with `UPDATE_SNAPSHOTS=true` via manual dispatch
2. Review the generated screenshots in the workflow artifacts
3. Commit the updated baselines with a message referencing the visual change
4. Format: `chore(e2e): update visual baselines — [description of UI change]`

### When to Update

Update baselines **only** when:

- Intentional UI changes are merged (new components, layout changes, theme updates)
- Design system tokens change (colors, spacing, typography)
- New pages are added (add corresponding tests to `visual-regression.spec.ts`)

**Never** update baselines to suppress flaky diffs. Investigate the root cause instead.

## Diff Thresholds

| Metric                  | Threshold                             | Action                                 |
| :---------------------- | :------------------------------------ | :------------------------------------- |
| Pixel diff ratio        | > 1% (`maxDiffPixelRatio: 0.01`)      | PR blocked                             |
| Missing baseline        | No baseline file exists               | PR blocked (`updateSnapshots: 'none'`) |
| New unreviewed baseline | Screenshot without committed baseline | PR blocked                             |

## Performance Thresholds

| Page         | Metric | Threshold |
| :----------- | :----- | :-------- |
| `/pricing`   | FCP    | ≤ 1800ms  |
| `/pricing`   | LCP    | ≤ 2500ms  |
| `/dashboard` | FCP    | ≤ 2000ms  |
| `/dashboard` | LCP    | ≤ 3000ms  |

## Accessibility Requirements

- Zero critical or serious violations per `@axe-core/playwright`
- WCAG 2.1 AA compliance
- Violations logged in CI output for debugging

## Approval Process

1. **Author**: Reviews diff screenshots in CI artifacts
2. **Reviewer**: Confirms visual changes align with the PR's intent
3. **Both sign off** before merge

## Deterministic Rendering

All visual tests enforce:

- **Clock freeze**: All timestamps frozen to `2026-01-15T10:00:00Z`
- **Animation kill**: CSS `animation-duration: 0s; transition-duration: 0s`
- **API mocking**: All backend calls return deterministic seeded data
- **Auth bypass**: Seeded JWT tokens in localStorage
- **Font stabilization**: Wait for `document.fonts.ready`
- **Scroll reset**: `window.scrollTo(0, 0)` before each screenshot

## File Structure

```
apps/web/e2e/
├── visual-regression.spec.ts    # 14 screenshot tests
├── performance-baseline.spec.ts # FCP/LCP + accessibility
├── visual-fixtures.ts           # Deterministic rendering fixtures
├── fixtures/
│   └── mock-api-data.ts         # Seeded API responses
└── __screenshots__/             # Git-tracked baselines (CI-captured)
```

## Troubleshooting

| Symptom                           | Cause                      | Fix                                              |
| :-------------------------------- | :------------------------- | :----------------------------------------------- |
| All tests show login page         | Auth tokens not seeded     | Check `visual-fixtures.ts` addInitScript         |
| Skeleton-only screenshots         | API mocks not intercepting | Verify `localhost:8000` route matching           |
| Flaky 1-pixel diffs               | Font rendering variance    | Increase `maxDiffPixelRatio` or re-capture in CI |
| `updateSnapshots: 'none'` failure | No baseline committed      | Run with `UPDATE_SNAPSHOTS=true` once in CI      |
