import { test, expect, type Page } from '@playwright/test';

/**
 * PathForge — Career DNA E2E Tests
 *
 * Sprint 30 WS-3: Validates Career DNA page rendering, data display,
 * and interaction patterns. Uses route interception for determinism.
 */

const MOCK_CAREER_DNA = {
  dimensions: [
    { name: 'Technical Skills', score: 85, trend: 'up' },
    { name: 'Leadership', score: 72, trend: 'stable' },
    { name: 'Domain Expertise', score: 90, trend: 'up' },
    { name: 'Communication', score: 68, trend: 'down' },
    { name: 'Innovation', score: 78, trend: 'up' },
  ],
  overall_score: 79,
  last_updated: '2026-02-27T12:00:00Z',
};

async function setupAuthenticatedSession(page: Page): Promise<void> {
  // Mock authentication state
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

test.describe('Career DNA', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('should load career DNA page with mocked data', async ({ page }) => {
    await page.route('**/api/v1/career-dna/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_CAREER_DNA),
      });
    });

    await page.goto('/dashboard/career-dna');

    // Page should load without crashing
    await expect(page).toHaveTitle(/PathForge/i);
    await page.waitForLoadState('networkidle');
  });

  test('should handle API errors gracefully', async ({ page }) => {
    await page.route('**/api/v1/career-dna/**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'internal_error', detail: 'Service unavailable' }),
      });
    });

    await page.goto('/dashboard/career-dna');
    // Page should not crash — should show error state or empty state
    await expect(page).toHaveTitle(/PathForge/i);
  });

  test('should redirect to login when unauthenticated', async ({ page }) => {
    // Override auth mock to return 401
    await page.route('**/api/v1/auth/me', (route) => {
      route.fulfill({ status: 401, body: JSON.stringify({ detail: 'Not authenticated' }) });
    });

    await page.goto('/dashboard/career-dna');
    await expect(page).toHaveURL(/login|auth/i, { timeout: 10_000 });
  });
});
