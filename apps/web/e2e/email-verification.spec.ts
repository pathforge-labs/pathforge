import { test, expect } from '@playwright/test';

/**
 * PathForge — Email Verification E2E Tests
 * ==========================================
 * Flow: Register → Check Email → Verify Email
 *
 * C1 Fix: Register page uses authApi.register() directly and redirects
 * to /check-email — does NOT use AuthProvider.register() which auto-logs-in.
 */

test.describe('Email Verification Flow', () => {
  // ── Registration ────────────────────────────────────────────

  test('should register and redirect to check-email', async ({ page }) => {
    // Mock successful registration
    await page.route('**/api/v1/auth/register', (route) =>
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'new-user-001',
          email: 'newuser@pathforge.test',
          full_name: 'New User',
          is_active: true,
          is_verified: false,
          auth_provider: 'email',
          avatar_url: null,
          created_at: '2026-03-17T00:00:00Z',
        }),
      }),
    );

    await page.goto('/register');

    await page.getByLabel('Full Name').fill('New User');
    await page.getByLabel('Email').fill('newuser@pathforge.test');
    await page.getByLabel('Password', { exact: true }).fill('SecurePass1!');
    await page.getByLabel('Confirm Password').fill('SecurePass1!');
    await page.getByRole('button', { name: /create account/i }).click();

    // C1: Register page redirects to /check-email with email param
    await expect(page).toHaveURL(/check-email/i, { timeout: 10_000 });
    await expect(page.getByText('newuser@pathforge.test')).toBeVisible();
  });

  test('should show error on password mismatch', async ({ page }) => {
    await page.goto('/register');

    await page.getByLabel('Full Name').fill('Test User');
    await page.getByLabel('Email').fill('test@example.com');
    await page.getByLabel('Password', { exact: true }).fill('SecurePass1!');
    await page.getByLabel('Confirm Password').fill('DifferentPass1!');
    await page.getByRole('button', { name: /create account/i }).click();

    await expect(page.getByText(/passwords do not match/i)).toBeVisible();
  });

  test('should show error on weak password', async ({ page }) => {
    await page.goto('/register');

    await page.getByLabel('Full Name').fill('Test User');
    await page.getByLabel('Email').fill('test@example.com');
    // 12 chars passes HTML5 minLength=8, but fails complexity (no uppercase/digit/special)
    await page.getByLabel('Password', { exact: true }).fill('weakpassword');
    await page.getByLabel('Confirm Password').fill('weakpassword');
    await page.getByRole('button', { name: /create account/i }).click();

    await expect(
      page.getByText(/password must contain/i).first(),
    ).toBeVisible({ timeout: 5_000 });
  });

  test('should show error on duplicate email registration', async ({ page }) => {
    // Mock 409 Conflict
    await page.route('**/api/v1/auth/register', (route) =>
      route.fulfill({
        status: 409,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Email already registered' }),
      }),
    );

    await page.goto('/register');

    await page.getByLabel('Full Name').fill('Existing User');
    await page.getByLabel('Email').fill('existing@pathforge.test');
    await page.getByLabel('Password', { exact: true }).fill('SecurePass1!');
    await page.getByLabel('Confirm Password').fill('SecurePass1!');
    await page.getByRole('button', { name: /create account/i }).click();

    await expect(page.getByText(/already registered/i)).toBeVisible({
      timeout: 5_000,
    });
  });

  // ── Check Email Page ────────────────────────────────────────

  test('should display email from URL parameter', async ({ page }) => {
    await page.goto('/check-email?email=user%40pathforge.test');

    await expect(page.getByText('user@pathforge.test')).toBeVisible();
    await expect(page.getByText(/check your email/i)).toBeVisible();
    await expect(page.getByRole('link', { name: /go to login/i })).toBeVisible();
  });

  // ── Email Verification ──────────────────────────────────────

  test('should verify email with valid token', async ({ page }) => {
    // Route must be set BEFORE navigating — useEffect fires on mount
    await page.route('**/api/v1/auth/verify-email', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ message: 'Email verified successfully' }),
      }),
    );

    // Navigate and wait for the API call to complete
    await Promise.all([
      page.waitForResponse((res) => res.url().includes('/verify-email') && res.status() === 200),
      page.goto('/verify-email?token=valid-verification-token'),
    ]);

    // Success state: "Email verified! 🎉" heading and "Sign in" button
    await expect(page.getByText(/email verified/i)).toBeVisible({
      timeout: 15_000,
    });
    await expect(
      page.getByRole('button', { name: /sign in/i }),
    ).toBeVisible();
  });

  test('should show error without token', async ({ page }) => {
    await page.goto('/verify-email');

    await expect(page.getByText(/invalid verification link/i)).toBeVisible();
    await expect(
      page.getByRole('button', { name: /go to login/i }),
    ).toBeVisible();
  });

  test('should show error with expired token', async ({ page }) => {
    // Route must be set BEFORE navigating — useEffect fires on mount
    await page.route('**/api/v1/auth/verify-email', (route) =>
      route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({
          detail: 'Verification token has expired',
        }),
      }),
    );

    // Navigate and wait for the API response
    await Promise.all([
      page.waitForResponse((res) => res.url().includes('/verify-email')),
      page.goto('/verify-email?token=expired-token'),
    ]);

    // Error state: "Verification failed" heading
    await expect(page.getByText(/verification failed|expired/i)).toBeVisible({
      timeout: 15_000,
    });
  });
});
