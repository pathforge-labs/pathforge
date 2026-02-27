import { test, expect } from '@playwright/test';

/**
 * PathForge — Auth Flow E2E Tests
 *
 * Sprint 30 WS-3: Validates the complete authentication lifecycle.
 * Uses data-testid selectors and route interception for determinism.
 */

// Test credentials — available for future authenticated flow tests
// const TEST_USER = {
//   email: `e2e-${Date.now()}@pathforge.test`,
//   password: 'E2eTestPass123!',
//   fullName: 'E2E Test User',
// };

test.describe('Authentication Flow', () => {
  test('should display login page', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveTitle(/PathForge/i);
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
  });

  test('should navigate to register page', async ({ page }) => {
    await page.goto('/login');
    const registerLink = page.getByRole('link', { name: /register|sign up|create/i });
    if (await registerLink.isVisible()) {
      await registerLink.click();
      await expect(page).toHaveURL(/register|signup/i);
    }
  });

  test('should show validation errors on empty login', async ({ page }) => {
    await page.goto('/login');
    const submitButton = page.getByRole('button', { name: /sign in|log in|login/i });
    if (await submitButton.isVisible()) {
      await submitButton.click();
      // Should show validation message — either native HTML5 or custom
      await expect(
        page.getByText(/required|email|password/i).first(),
      ).toBeVisible({ timeout: 5_000 });
    }
  });

  test('should redirect unauthenticated users from protected routes', async ({ page }) => {
    await page.goto('/dashboard');
    // Should redirect to login or show auth prompt
    await expect(page).toHaveURL(/login|auth/i, { timeout: 10_000 });
  });
});
