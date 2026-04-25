import { test, expect } from '@playwright/test';
import {
  setupAuthenticatedSession,
  MOCK_TOKENS,
} from './fixtures/auth';

/**
 * PathForge — Logout E2E Tests
 * ==============================
 * Flow: Authenticated Dashboard → Logout → Session End
 *
 * C3: Mocks POST /api/v1/auth/logout for server-side token revocation.
 * Uses shared fixture setupAuthenticatedSession — identical to dashboard tests.
 *
 * Architecture Note: Dashboard rendering time varies under parallel workers.
 * Using generous timeout (30s) for Sign Out button visibility.
 */

// Run serially — dashboard state + logout is sequential by nature
test.describe.configure({ mode: 'serial' });

test.describe('Logout Flow', () => {
  test.beforeEach(async ({ page }) => {
    // C3: Mock logout endpoint (server-side token revocation)
    await page.route('**/api/v1/auth/logout', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Logged out successfully' }),
      }),
    );

    await setupAuthenticatedSession(page);
  });

  test('should show logout button on dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    // A8: Logout button has title="Sign out"
    await expect(page.getByTitle('Sign out')).toBeVisible({ timeout: 30_000 });
  });

  test('should clear tokens on logout', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByTitle('Sign out')).toBeVisible({ timeout: 30_000 });

    // Verify tokens exist before logout
    const tokensBefore = await page.evaluate(() => ({
      access: localStorage.getItem('pathforge_access_token'),
      refresh: localStorage.getItem('pathforge_refresh_token'),
    }));
    expect(tokensBefore.access).toBe(MOCK_TOKENS.access_token);
    expect(tokensBefore.refresh).toBe(MOCK_TOKENS.refresh_token);

    // Click logout
    await page.getByTitle('Sign out').click();

    // Wait for navigation to login
    await expect(page).toHaveURL(/login/i, { timeout: 15_000 });

    // Verify tokens are cleared
    const tokensAfter = await page.evaluate(() => ({
      access: localStorage.getItem('pathforge_access_token'),
      refresh: localStorage.getItem('pathforge_refresh_token'),
    }));
    expect(tokensAfter.access).toBeNull();
    expect(tokensAfter.refresh).toBeNull();
  });

  test('should redirect to login after logout', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page.getByTitle('Sign out')).toBeVisible({ timeout: 30_000 });

    await page.getByTitle('Sign out').click();
    await expect(page).toHaveURL(/login/i, { timeout: 15_000 });
  });
});

/**
 * Session Invalidation — Redirect unauthenticated users from protected routes
 * (No authenticated session setup — tests guard behavior)
 */
test.describe('Session Guard', () => {
  test('should redirect from dashboard when not authenticated', async ({ page }) => {
    // Navigate directly to dashboard without any tokens
    await page.goto('/dashboard');

    // Dashboard layout should redirect to login when no tokens present
    await expect(page).toHaveURL(/login/i, { timeout: 15_000 });
  });
});
