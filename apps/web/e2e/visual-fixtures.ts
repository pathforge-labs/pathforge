/* eslint-disable react-hooks/rules-of-hooks */
/**
 * PathForge — Visual Regression Fixtures
 * ========================================
 * Sprint 36 WS-7: Deterministic Playwright fixtures for visual regression testing.
 *
 * Guarantees:
 *   1. Auth bypass — seeds localStorage JWT tokens before page load
 *   2. API interception — all localhost:8000 calls return seeded JSON
 *   3. Animation/transition kill — CSS injection prevents render flakiness
 *   4. Clock freeze — eliminates timestamp-based rendering drift
 *   5. Font stabilization — waits for document.fonts.ready
 *   6. Scroll reset — ensures consistent viewport starting position
 */

import { test as base, type Page } from "@playwright/test";
import { API_ROUTE_MAP } from "./fixtures/mock-api-data";

/* ── Types ────────────────────────────────────────────────── */

interface VisualFixtures {
  /** Pre-configured page with auth, API mocking, and determinism applied. */
  visualPage: Page;
}

/* ── Constants ────────────────────────────────────────────── */

// In local dev, API_BASE_URL defaults to http://localhost:8000 (CSP allows it).
// In CI VR builds, NEXT_PUBLIC_API_URL=http://localhost:3000 is set so the
// production-mode CSP ('self' only) doesn't block fetches. Both origins are
// intercepted here so the same fixture works in both environments.
const BACKEND_ORIGIN = "http://localhost:8000";
const VR_CI_ORIGIN = "http://localhost:3000";

/**
 * CSS injection to kill all animations and transitions.
 * Applied via page.addStyleTag for maximum specificity.
 */
const DETERMINISTIC_CSS = `
  *, *::after, *::before {
    animation-duration: 0s !important;
    animation-delay: 0s !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
    scroll-behavior: auto !important;
  }
`;

/* ── Route Handler ────────────────────────────────────────── */

/**
 * Intercepts backend API calls and returns deterministic mock data.
 * Falls back to empty JSON for unmapped routes (prevents 404 errors).
 */
async function handleApiRoute(route: { request: () => { url: () => string }; fulfill: (response: { status: number; contentType: string; body: string }) => Promise<void> }): Promise<void> {
  const url = new URL(route.request().url());
  const pathname = url.pathname;

  // Find matching mock response
  const mockResponse = API_ROUTE_MAP[pathname];

  if (mockResponse !== undefined) {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(mockResponse),
    });
  } else {
    // Fallback: return empty JSON for unmapped API routes
    console.warn(`[VR] Unmapped API route: ${pathname}`);
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({}),
    });
  }
}

/* ── Fixture Definition ──────────────────────────────────── */

export const test = base.extend<VisualFixtures>({
  visualPage: async ({ browser }, use) => {
    // 1. Create context with deterministic settings
    const context = await browser.newContext({
      viewport: { width: 1280, height: 720 },
      colorScheme: "light",
      reducedMotion: "reduce",
      locale: "en-US",
      timezoneId: "UTC",
    });

    const page = await context.newPage();

    // 2. Seed auth tokens BEFORE any page navigation
    //    token-manager.ts hydrates from localStorage on module init,
    //    so tokens must be present before the page script loads.
    await page.addInitScript(() => {
      localStorage.setItem("pathforge_access_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ2ci11c2VyLTAwMSIsImV4cCI6OTk5OTk5OTk5OX0.mock");
      localStorage.setItem("pathforge_refresh_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ2ci11c2VyLTAwMSIsInR5cGUiOiJyZWZyZXNoIn0.mock");
    });

    // 3. Intercept backend API calls.
    //    - localhost:8000: local dev (CSP allows it in dev mode)
    //    - localhost:3000/api/*: CI VR builds (NEXT_PUBLIC_API_URL=localhost:3000,
    //      Playwright intercepts before Next.js rewrite proxy kicks in)
    await page.route(
      (url) =>
        url.origin === BACKEND_ORIGIN ||
        (url.origin === VR_CI_ORIGIN && url.pathname.startsWith("/api/")),
      handleApiRoute,
    );

    // 4. Fix Date.now() to eliminate timestamp drift in rendered UI.
    //    setFixedTime pins Date/Date.now() without replacing setTimeout or
    //    requestAnimationFrame — those are needed by React's concurrent
    //    scheduler. Using clock.install() would freeze rAF and break
    //    React state updates, causing waitForSelector("h1") to time out.
    await page.clock.setFixedTime(new Date("2026-01-15T10:00:00Z"));

    // 5. Pass page to test — auth + API interception active
    await use(page);

    // Cleanup
    await context.close();
  },
});

/* ── Helper: Stabilize Page for Screenshot ───────────────── */

/**
 * Applies final stabilization before taking a screenshot:
 *   - Injects CSS to kill animations/transitions
 *   - Waits for all fonts to load
 *   - Scrolls to top
 *   - Settles for 300ms to allow final renders
 */
export async function stabilizeForScreenshot(page: Page): Promise<void> {
  // Inject deterministic CSS
  await page.addStyleTag({ content: DETERMINISTIC_CSS });

  // Wait for fonts
  await page.evaluate(() => document.fonts.ready);

  // Scroll to top
  await page.evaluate(() => window.scrollTo(0, 0));

  // Allow final renders to settle
  await page.waitForTimeout(300);
}

/* ── Helper: Navigate and Wait for Data ──────────────────── */

/**
 * Navigates to a page and waits for a specific content selector
 * to appear, confirming that API data has been rendered.
 *
 * Uses content-based waiting instead of `networkidle` to avoid
 * false positives from long-polling or background requests.
 */
export async function navigateAndWait(
  page: Page,
  path: string,
  contentSelector: string,
  timeout: number = 30_000,
): Promise<void> {
  await page.goto(path, { waitUntil: "domcontentloaded" });
  await page.waitForSelector(contentSelector, { timeout });
}

/* ── Re-export expect ────────────────────────────────────── */

export { expect } from "@playwright/test";
