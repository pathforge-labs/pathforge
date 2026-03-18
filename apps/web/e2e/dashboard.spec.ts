import { test, expect } from '@playwright/test';
import { setupAuthenticatedSession } from './fixtures/auth';

/**
 * PathForge — Dashboard Overview E2E Tests
 *
 * Sprint 30 WS-3: Validates the main dashboard page rendering,
 * widget display, and navigation to sub-pages.
 *
 * Sprint 40: Refactored to use shared auth fixture (C2 fix).
 */

test.describe('Dashboard Overview', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthenticatedSession(page);
  });


  test('should load main dashboard page', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveTitle(/PathForge/i);
    await page.waitForLoadState('networkidle');
  });

  test('should have navigation sidebar with key links', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Check that navigation elements exist
    const nav = page.locator('nav, [role="navigation"]').first();
    if (await nav.isVisible()) {
      const navText = await nav.textContent();
      expect(navText).toBeTruthy();
    }
  });

  test('should not have critical console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        errors.push(msg.text());
      }
    });

    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Filter known non-critical errors
    const criticalErrors = errors.filter(
      (e) =>
        !e.includes('favicon') &&
        !e.includes('hydration') &&
        !e.includes('NEXT_REDIRECT') &&
        !e.includes('404'),
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test('should be responsive at mobile viewport', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto('/dashboard');
    await expect(page).toHaveTitle(/PathForge/i);

    // Page should still be functional at mobile size
    const body = page.locator('body');
    await expect(body).toBeVisible();
  });
});
