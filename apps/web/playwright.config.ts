import { defineConfig, devices } from '@playwright/test';

/**
 * PathForge — Playwright E2E Configuration
 *
 * Sprint 30 WS-3: E2E testing with anti-flake measures (Audit M1).
 * - Pinned Playwright version (set in package.json)
 * - Explicit timeouts
 * - CI-only screenshot baselines
 * - Animations disabled for deterministic screenshots
 *
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
      // Audit M1: Increased tolerance to prevent flakiness
      maxDiffPixelRatio: 0.02,
    },
  },

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',

    // Audit M1: Disable animations for deterministic screenshots
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
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
  ],

  // Start local dev server for E2E tests
  webServer: process.env.CI
    ? undefined // CI serves pre-built app
    : {
        command: 'pnpm dev',
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
        timeout: 60_000,
      },
});
