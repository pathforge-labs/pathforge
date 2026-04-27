import { defineConfig, devices } from '@playwright/test';

/**
 * PathForge — Playwright E2E Configuration
 *
 * Sprint 30 WS-3: E2E testing with anti-flake measures (Audit M1).
 * Sprint 36 WS-7: Visual regression baselines with deterministic rendering.
 *
 * - Pinned Playwright version (set in package.json)
 * - Explicit timeouts
 * - CI-only screenshot baselines with strict comparison
 * - Animations disabled for deterministic screenshots
 * - webServer config for both local dev and CI production builds
 *
 * @see docs/visual-regression-policy.md
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? 'github' : 'html',

  // Global timeouts
  timeout: 30_000,
  expect: {
    timeout: 10_000,
    toHaveScreenshot: {
      // Sprint 36 WS-7: 1% tolerance for CI font rendering variance
      maxDiffPixelRatio: 0.01,
    },
    toMatchSnapshot: {
      maxDiffPixelRatio: 0.01,
    },
  },

  // Sprint 36 WS-7: Snapshot path template for visual regression
  snapshotPathTemplate: '{testDir}/__screenshots__/{testFilePath}/{arg}{ext}',

  // Sprint 36 WS-7: Strict snapshot comparison in CI
  //   - 'all'  → capture/update baselines (manual workflow dispatch only)
  //   - 'none' → strict comparison, fail on any new/missing baseline
  updateSnapshots: process.env.UPDATE_SNAPSHOTS === 'true' ? 'all' : 'none',

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Audit M1: Disable animations for deterministic screenshots
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        // Disable CSS animations/transitions for screenshot stability
        launchOptions: {
          args: ['--force-prefers-reduced-motion'],
        },
      },
    },
    // Sprint 36 WS-7: Mobile viewport for responsive visual tests
    {
      name: 'mobile',
      use: {
        ...devices['iPhone 13'],
        colorScheme: 'light',
        launchOptions: {
          args: ['--force-prefers-reduced-motion'],
        },
      },
    },
  ],

  // Sprint 36 WS-7 / Sprint 61 PR #47 / PR #48 (this refactor):
  // webServer config for both local dev and CI.
  //
  // Prod-smoke (Sprint 58, ADR-0010) targets remote production
  // hosts via PROD_SMOKE_*_BASE_URL env vars and never uses
  // Playwright's `baseURL`. Spinning up a local Next server in
  // that mode would (a) require an extra `pnpm build` step in the
  // workflow and (b) fail anyway because the smoke job intentionally
  // doesn't build the app. Setting PROD_SMOKE=true bypasses the
  // webServer entirely.
  //
  // Flattened from a nested ternary (PR #47 → Gemini medium #1).
  // PR #48 → Gemini medium #1: read the same ``E2E_BASE_URL``
  // override the test runner uses (line 48) so an operator who
  // points the suite at, say, ``http://localhost:4000`` doesn't
  // see Playwright spawn ``pnpm dev`` and then time out polling
  // port 3000 while the actual server is on 4000.
  //
  //   - Single ternary on PROD_SMOKE — undefined vs. configured.
  //   - The configured branch picks `command` and `timeout` by
  //     ``process.env.CI``; everything else is shared.
  //   - ``url`` falls back to ``E2E_BASE_URL`` so the health-check
  //     target stays in lock-step with the test-runner ``baseURL``.
  //     Polling the URL (not just the port) catches the
  //     "server started but error-pages-only" failure class.
  webServer:
    process.env.PROD_SMOKE === 'true'
      ? undefined
      : {
          command: process.env.CI ? 'pnpm start' : 'pnpm dev',
          url: process.env.E2E_BASE_URL || 'http://localhost:3000',
          timeout: process.env.CI ? 30_000 : 60_000,
          reuseExistingServer: !process.env.CI,
        },
});
