/**
 * PathForge — E2E Auth Fixtures
 * ==============================
 * Shared helpers for authenticated E2E test sessions.
 *
 * C2 Fix: Uses `/api/v1/users/me` (the real AuthProvider endpoint),
 * NOT `/api/v1/auth/me` which was incorrect in dashboard.spec.ts.
 *
 * Architecture Note: The token-manager hydrates its in-memory cache
 * on module load (hydrateFromStorage). Setting localStorage via
 * page.evaluate after load does NOT update the cache. Therefore,
 * this fixture sets up routes, navigates to establish origin,
 * injects tokens into localStorage, then reloads the page to
 * trigger re-hydration.
 */

import type { Page } from '@playwright/test';

// ── Mock Data ───────────────────────────────────────────────

export const MOCK_USER = {
  id: 'test-user-001',
  email: 'e2e@pathforge.test',
  full_name: 'E2E Test User',
  is_active: true,
  is_verified: true,
  auth_provider: 'email',
  avatar_url: null,
  created_at: '2026-01-01T00:00:00Z',
} as const;

export const MOCK_TOKENS = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
} as const;

export const MOCK_ONBOARDING = {
  profile_complete: true,
  resume_uploaded: true,
  career_dna_generated: true,
  steps_completed: 4,
  total_steps: 4,
} as const;

// ── Helpers ─────────────────────────────────────────────────

/**
 * Set up an authenticated session for E2E tests.
 *
 * Sequence:
 * 1. Register API route mocks (before any navigation)
 * 2. Navigate to /login to establish browser origin
 * 3. Inject tokens into localStorage
 * 4. DO NOT reload — let each test navigate to its target page
 *    (full navigation re-initializes the token-manager module cache)
 *
 * IMPORTANT: After calling this, navigate with page.goto() (not router.push)
 * so the token-manager module re-hydrates its in-memory cache.
 */
export async function setupAuthenticatedSession(page: Page): Promise<void> {
  // C2 Fix: AuthProvider uses /users/me, not /auth/me
  await page.route('**/api/v1/users/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_USER),
    }),
  );

  await page.route('**/api/v1/users/onboarding-status', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(MOCK_ONBOARDING),
    }),
  );

  // Generic fallback for other API calls (dashboard widgets, etc.)
  await page.route('**/api/v1/**', (route) => {
    const url = route.request().url();
    if (url.includes('/auth/') || url.includes('/users/')) {
      return route.fallback();
    }
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ data: [], total: 0 }),
    });
  });

  // Navigate to establish origin, then inject tokens
  await page.goto('/login');
  await page.evaluate(({ access, refresh }) => {
    localStorage.setItem('pathforge_access_token', access);
    localStorage.setItem('pathforge_refresh_token', refresh);
  }, { access: MOCK_TOKENS.access_token, refresh: MOCK_TOKENS.refresh_token });
}

/**
 * Collect non-trivial console errors during a test.
 * Filters known non-critical errors (favicon, hydration, NEXT_REDIRECT, 404).
 */
export function createConsoleErrorCollector(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      const text = msg.text();
      const isIgnorable =
        text.includes('favicon') ||
        text.includes('hydration') ||
        text.includes('NEXT_REDIRECT') ||
        text.includes('404');
      if (!isIgnorable) {
        errors.push(text);
      }
    }
  });
  return errors;
}
