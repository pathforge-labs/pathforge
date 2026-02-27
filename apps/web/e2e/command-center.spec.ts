import { test, expect, type Page } from '@playwright/test';

/**
 * PathForge — Command Center E2E Tests
 *
 * Sprint 30 WS-3: Validates Command Center page with engine status
 * display and system health overview.
 */

const MOCK_ENGINE_STATUS = {
  engines: [
    { name: 'Career DNA Engine', status: 'operational', latency_ms: 120 },
    { name: 'Threat Radar Engine', status: 'operational', latency_ms: 95 },
    { name: 'Job Aggregation Engine', status: 'degraded', latency_ms: 2500 },
    { name: 'Resume Parser Engine', status: 'operational', latency_ms: 340 },
  ],
  overall_status: 'degraded',
  last_checked: '2026-02-27T12:00:00Z',
};

async function setupAuthenticatedSession(page: Page): Promise<void> {
  await page.route('**/api/v1/auth/me', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'test-user-id',
        email: 'e2e@pathforge.test',
        full_name: 'E2E Test User',
      }),
    });
  });
}

test.describe('Command Center', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('should load command center page', async ({ page }) => {
    await page.route('**/api/v1/command-center/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_ENGINE_STATUS),
      });
    });

    await page.goto('/dashboard/command-center');
    await expect(page).toHaveTitle(/PathForge/i);
    await page.waitForLoadState('networkidle');
  });

  test('should handle all engines down scenario', async ({ page }) => {
    await page.route('**/api/v1/command-center/**', (route) => {
      route.fulfill({
        status: 503,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'all_engines_down', detail: 'System maintenance' }),
      });
    });

    await page.goto('/dashboard/command-center');
    // Page should render error state, not crash
    await expect(page).toHaveTitle(/PathForge/i);
  });

  test('should not have console errors on load', async ({ page }) => {
    await page.route('**/api/v1/command-center/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_ENGINE_STATUS),
      });
    });

    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/dashboard/command-center');
    await page.waitForLoadState('networkidle');

    // Filter known non-critical errors (favicon, hydration)
    const criticalErrors = errors.filter(
      (e) => !e.includes('favicon') && !e.includes('hydration'),
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test('should redirect to login when unauthenticated', async ({ page }) => {
    await page.route('**/api/v1/auth/me', (route) => {
      route.fulfill({ status: 401, body: JSON.stringify({ detail: 'Not authenticated' }) });
    });

    await page.goto('/dashboard/command-center');
    await expect(page).toHaveURL(/login|auth/i, { timeout: 10_000 });
  });
});
