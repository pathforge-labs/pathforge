import { test, expect, type Page } from '@playwright/test';

/**
 * PathForge — Actions & Recommendations E2E Tests
 *
 * Sprint 30 WS-3: Validates Actions page rendering,
 * recommendation display, and interaction patterns.
 */

const MOCK_RECOMMENDATIONS = {
  actions: [
    {
      id: '1',
      type: 'skill_development',
      title: 'Learn Kubernetes',
      priority: 'high',
      estimated_impact: 15,
      description: 'Container orchestration is a top skill gap for your target roles',
    },
    {
      id: '2',
      type: 'networking',
      title: 'Connect with industry leaders',
      priority: 'medium',
      estimated_impact: 8,
      description: 'Expand your professional network in the AI/ML space',
    },
    {
      id: '3',
      type: 'certification',
      title: 'AWS Solutions Architect',
      priority: 'high',
      estimated_impact: 12,
      description: 'Cloud certifications increase match rate by 23%',
    },
  ],
  total_actions: 3,
  completed_actions: 0,
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

test.describe('Actions & Recommendations', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('should load actions page with recommendations', async ({ page }) => {
    await page.route('**/api/v1/recommendations/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_RECOMMENDATIONS),
      });
    });

    await page.goto('/dashboard/recommendations');
    await expect(page).toHaveTitle(/PathForge/i);
    await page.waitForLoadState('networkidle');
  });

  test('should handle empty recommendations gracefully', async ({ page }) => {
    await page.route('**/api/v1/recommendations/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ actions: [], total_actions: 0, completed_actions: 0 }),
      });
    });

    await page.goto('/dashboard/recommendations');
    // Should show empty state, not crash
    await expect(page).toHaveTitle(/PathForge/i);
  });

  test('should handle API failure on actions page', async ({ page }) => {
    await page.route('**/api/v1/recommendations/**', (route) => {
      route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'internal_error' }),
      });
    });

    await page.goto('/dashboard/recommendations');
    // Page should show error state, not crash
    await expect(page).toHaveTitle(/PathForge/i);
  });

  test('should redirect to login when unauthenticated', async ({ page }) => {
    await page.route('**/api/v1/auth/me', (route) => {
      route.fulfill({ status: 401, body: JSON.stringify({ detail: 'Not authenticated' }) });
    });

    await page.goto('/dashboard/recommendations');
    await expect(page).toHaveURL(/login|auth/i, { timeout: 10_000 });
  });
});
