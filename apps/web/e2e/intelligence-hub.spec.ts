import { test, expect, type Page } from '@playwright/test';

/**
 * PathForge — Intelligence Hub E2E Tests
 *
 * Sprint 30 WS-3: Validates Intelligence Hub pages (Skill Decay,
 * Salary Intelligence, Career Simulation, Transition Pathways).
 * These were added in Sprint 27 and need E2E coverage.
 */

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

  // Generic mock for all Intelligence Hub API endpoints
  await page.route('**/api/v1/**', (route) => {
    if (route.request().url().includes('/auth/')) {
      return route.fallback();
    }
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: [], total: 0, score: 0 }),
    });
  });
}

test.describe('Intelligence Hub — Skill Decay', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('should load skill decay page', async ({ page }) => {
    await page.goto('/dashboard/skill-decay');
    await expect(page).toHaveTitle(/PathForge/i);
    await page.waitForLoadState('networkidle');
  });

  test('should redirect to login when unauthenticated', async ({ page }) => {
    await page.route('**/api/v1/auth/me', (route) => {
      route.fulfill({ status: 401, body: JSON.stringify({ detail: 'Not authenticated' }) });
    });

    await page.goto('/dashboard/skill-decay');
    await expect(page).toHaveURL(/login|auth/i, { timeout: 10_000 });
  });
});

test.describe('Intelligence Hub — Salary Intelligence', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('should load salary intelligence page', async ({ page }) => {
    await page.goto('/dashboard/salary-intelligence');
    await expect(page).toHaveTitle(/PathForge/i);
    await page.waitForLoadState('networkidle');
  });
});

test.describe('Intelligence Hub — Career Simulation', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('should load career simulation page', async ({ page }) => {
    await page.goto('/dashboard/career-simulation');
    await expect(page).toHaveTitle(/PathForge/i);
    await page.waitForLoadState('networkidle');
  });
});

test.describe('Intelligence Hub — Transition Pathways', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });

  test('should load transition pathways page', async ({ page }) => {
    await page.goto('/dashboard/transition-pathways');
    await expect(page).toHaveTitle(/PathForge/i);
    await page.waitForLoadState('networkidle');
  });
});
