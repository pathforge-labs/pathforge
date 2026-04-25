import { test, expect } from '@playwright/test';

/**
 * PathForge — Password Recovery E2E Tests
 * =========================================
 * Flow: Forgot Password → Reset Password
 *
 * Tests the complete password recovery lifecycle including
 * form submission, state transitions, client-side validation,
 * and token-based reset.
 */

test.describe('Password Recovery Flow', () => {
  // ── Forgot Password ─────────────────────────────────────────

  test('should submit email and show success state', async ({ page }) => {
    await page.route('**/api/v1/auth/forgot-password', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          message: 'If an account exists, a reset link has been sent.',
        }),
      }),
    );

    await page.goto('/forgot-password');

    await page.getByLabel('Email').fill('user@pathforge.test');
    await page.getByRole('button', { name: /send reset link/i }).click();

    // After submit, page transitions to success state
    await expect(page.getByText(/check your email/i)).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByText('user@pathforge.test')).toBeVisible();
  });

  test('should allow retry from success state', async ({ page }) => {
    await page.route('**/api/v1/auth/forgot-password', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Reset link sent.' }),
      }),
    );

    await page.goto('/forgot-password');
    await page.getByLabel('Email').fill('user@pathforge.test');
    await page.getByRole('button', { name: /send reset link/i }).click();

    // Wait for success state
    await expect(page.getByText(/check your email/i)).toBeVisible({
      timeout: 10_000,
    });

    // Click "Try again" to go back to form
    await page.getByRole('button', { name: /try again/i }).click();

    // Should be back on the form
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(
      page.getByRole('button', { name: /send reset link/i }),
    ).toBeVisible();
  });

  test('should navigate back to login', async ({ page }) => {
    await page.goto('/forgot-password');

    const loginLink = page.getByRole('link', { name: /sign in/i });
    await expect(loginLink).toBeVisible();
    await loginLink.click();

    await expect(page).toHaveURL(/login/i, { timeout: 10_000 });
  });

  // ── Reset Password ──────────────────────────────────────────

  test('should reset password with valid token', async ({ page }) => {
    await page.route('**/api/v1/auth/reset-password', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Password updated successfully' }),
      }),
    );

    await page.goto('/reset-password?token=valid-reset-token');

    await page.getByLabel('New Password').fill('NewSecurePass1!');
    await page.getByLabel('Confirm Password').fill('NewSecurePass1!');
    await page.getByRole('button', { name: /reset password/i }).click();

    // Success state
    await expect(page.getByText(/password reset/i)).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      page.getByRole('button', { name: /go to login/i }),
    ).toBeVisible();
  });

  test('should show error on mismatched passwords', async ({ page }) => {
    await page.goto('/reset-password?token=valid-token');

    await page.getByLabel('New Password').fill('NewSecurePass1!');
    await page.getByLabel('Confirm Password').fill('DifferentPass1!');
    await page.getByRole('button', { name: /reset password/i }).click();

    await expect(page.getByText(/passwords do not match/i)).toBeVisible();
  });

  test('should show error on weak password', async ({ page }) => {
    await page.goto('/reset-password?token=valid-token');

    // 12 chars passes HTML5 minLength=8, but fails complexity (no uppercase/digit/special)
    await page.getByLabel('New Password').fill('weakpassword');
    await page.getByLabel('Confirm Password').fill('weakpassword');
    await page.getByRole('button', { name: /reset password/i }).click();

    await expect(
      page.getByText(/password must contain/i).first(),
    ).toBeVisible({ timeout: 5_000 });
  });

  test('should show invalid link without token', async ({ page }) => {
    await page.goto('/reset-password');

    await expect(page.getByText(/invalid reset link/i)).toBeVisible();
    await expect(
      page.getByRole('link', { name: /request a new link/i }),
    ).toBeVisible();
  });

  test('should navigate to login after successful reset', async ({ page }) => {
    await page.route('**/api/v1/auth/reset-password', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Password updated' }),
      }),
    );

    await page.goto('/reset-password?token=valid-token');
    await page.getByLabel('New Password').fill('NewSecurePass1!');
    await page.getByLabel('Confirm Password').fill('NewSecurePass1!');
    await page.getByRole('button', { name: /reset password/i }).click();

    // Wait for success state
    await expect(page.getByText(/password reset/i)).toBeVisible({
      timeout: 10_000,
    });

    // Click "Go to Login"
    await page.getByRole('button', { name: /go to login/i }).click();
    await expect(page).toHaveURL(/login/i, { timeout: 10_000 });
  });
});
