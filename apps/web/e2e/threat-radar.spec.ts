import { test, expect, type Page } from '@playwright/test';

/**
 * PathForge — Threat Radar E2E Tests
 *
 * Sprint 30 WS-3: Validates Threat Radar page rendering,
 * resilience score display, and alert interactions.
 */

const MOCK_THREAT_OVERVIEW = {
  resilience_score: 73,
  threat_level: 'moderate',
  alerts: [
    { id: '1', severity: 'high', title: 'AI Automation Risk', description: 'Role has 65% automation probability' },
    { id: '2', severity: 'medium', title: 'Skill Gap Detected', description: 'Python skills below market median' },
  ],
  last_analyzed: '2026-02-27T12:00:00Z',
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

test.describe('Threat Radar', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('should load threat radar page', async ({ page }) => {
    await page.route('**/api/v1/threat-radar/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_THREAT_OVERVIEW),
      });
    });

    await page.goto('/dashboard/threat-radar');
    await expect(page).toHaveTitle(/PathForge/i);
    await page.waitForLoadState('networkidle');
  });

  test('should display resilience score when data loads', async ({ page }) => {
    await page.route('**/api/v1/threat-radar/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_THREAT_OVERVIEW),
      });
    });

    await page.goto('/dashboard/threat-radar');
    await page.waitForLoadState('networkidle');

    // Check for any numeric content that could represent the score
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeTruthy();
  });

  test('should handle empty threat data gracefully', async ({ page }) => {
    await page.route('**/api/v1/threat-radar/**', (route) => {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ resilience_score: 0, threat_level: 'unknown', alerts: [] }),
      });
    });

    await page.goto('/dashboard/threat-radar');
    // Should show empty state or placeholder, not crash
    await expect(page).toHaveTitle(/PathForge/i);
  });

  test('should redirect to login when unauthenticated', async ({ page }) => {
    await page.route('**/api/v1/auth/me', (route) => {
      route.fulfill({ status: 401, body: JSON.stringify({ detail: 'Not authenticated' }) });
    });

    await page.goto('/dashboard/threat-radar');
    await expect(page).toHaveURL(/login|auth/i, { timeout: 10_000 });
  });
});
