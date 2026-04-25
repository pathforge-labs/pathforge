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

  // Sprint 36 WS-7: webServer for both local dev and CI
  webServer: process.env.CI
    ? {
        // CI: serve the pre-built production bundle
        command: 'pnpm start',
        port: 3000,
        timeout: 30_000,
        reuseExistingServer: false,
      }
    : {
        // Local: start dev server
        command: 'pnpm dev',
        url: 'http://localhost:3000',
        reuseExistingServer: true,
        timeout: 60_000,
      },
});
