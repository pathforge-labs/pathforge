/**
 * PathForge — Visual Regression Tests
 * ========================================
 * Sprint 36 WS-7: Full-page screenshot baselines for 6 pages × 2 themes + 2 mobile views.
 *
 * Architecture:
 *   - Uses custom `visualPage` fixture for deterministic rendering
 *   - Auth bypass via seeded localStorage tokens
 *   - All API calls intercepted with stable mock data
 *   - Clock frozen, animations/transitions killed
 *
 * Coverage:
 *   14 tests: 6 desktop pages × 2 themes + 2 mobile views
 *
 * Baselines:
 *   - Must be captured in CI (Ubuntu) — never committed from local dev
 *   - First CI run: UPDATE_SNAPSHOTS=true via manual workflow dispatch
 *   - Subsequent runs: strict comparison, PR blocked on diff
 *
 * @see docs/visual-regression-policy.md
 */

import { test, expect, stabilizeForScreenshot, navigateAndWait } from "./visual-fixtures";

/* ── Page Definitions ────────────────────────────────────── */

interface PageDefinition {
  readonly name: string;
  readonly path: string;
  /** CSS selector confirming data has rendered (not just skeleton/loading). */
  readonly contentSelector: string;
}

const PAGES: readonly PageDefinition[] = [
  {
    name: "dashboard",
    path: "/dashboard",
    contentSelector: "h1",
  },
  {
    name: "career-dna",
    path: "/dashboard/career-dna",
    contentSelector: "h1",
  },
  {
    name: "threat-radar",
    path: "/dashboard/threat-radar",
    contentSelector: "h1",
  },
  {
    name: "recommendations",
    path: "/dashboard/recommendations",
    contentSelector: "h1",
  },
  {
    name: "career-passport",
    path: "/dashboard/career-passport",
    contentSelector: "h1",
  },
  {
    name: "pricing",
    path: "/pricing",
    contentSelector: "h1",
  },
] as const;

const THEMES = ["light", "dark"] as const;

/* ── Desktop Tests (6 pages × 2 themes = 12 tests) ──────── */

test.describe("Visual Regression — Desktop", () => {
  for (const page of PAGES) {
    for (const theme of THEMES) {
      test(`${page.name} (${theme})`, async ({ visualPage }) => {
        // Apply theme via color scheme
        await visualPage.emulateMedia({ colorScheme: theme });

        // Navigate and wait for content
        await navigateAndWait(visualPage, page.path, page.contentSelector);

        // Stabilize rendering
        await stabilizeForScreenshot(visualPage);

        // Capture screenshot
        await expect(visualPage).toHaveScreenshot(
          `${page.name}-${theme}.png`,
          {
            fullPage: true,
            maxDiffPixelRatio: 0.01,
          },
        );
      });
    }
  }
});

/* ── Mobile Tests (2 pages × 1 theme = 2 tests) ─────────── */

test.describe("Visual Regression — Mobile", () => {
  const MOBILE_PAGES: readonly PageDefinition[] = [
    {
      name: "pricing",
      path: "/pricing",
      contentSelector: "h1",
    },
    {
      name: "dashboard",
      path: "/dashboard",
      contentSelector: "h1",
    },
  ];

  for (const page of MOBILE_PAGES) {
    test(`${page.name} (mobile)`, async ({ browser }) => {
      // Create mobile-sized context with auth seeding
      const context = await browser.newContext({
        viewport: { width: 375, height: 812 },
        colorScheme: "light",
        reducedMotion: "reduce",
        locale: "en-US",
        timezoneId: "UTC",
        isMobile: true,
        hasTouch: true,
      });

      const mobilePage = await context.newPage();

      // Seed auth tokens
      await mobilePage.addInitScript(() => {
        localStorage.setItem("pathforge_access_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ2ci11c2VyLTAwMSIsImV4cCI6OTk5OTk5OTk5OX0.mock");
        localStorage.setItem("pathforge_refresh_token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ2ci11c2VyLTAwMSIsInR5cGUiOiJyZWZyZXNoIn0.mock");
      });

      // Intercept API calls — match both localhost:8000 (local dev) and
      // localhost:3000/api/* (CI builds where NEXT_PUBLIC_API_URL=localhost:3000)
      const { API_ROUTE_MAP } = await import("./fixtures/mock-api-data");
      await mobilePage.route(
        (url) =>
          url.origin === "http://localhost:8000" ||
          (url.origin === "http://localhost:3000" && url.pathname.startsWith("/api/")),
        async (route) => {
          const pathname = new URL(route.request().url()).pathname;
          const mock = API_ROUTE_MAP[pathname];
          await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify(mock ?? {}),
          });
        },
      );

      // Pin Date.now() without freezing RAF/setTimeout (same as visualPage fixture).
      // clock.install() freezes requestAnimationFrame which breaks React's concurrent
      // scheduler and prevents auth state updates from re-rendering.
      await mobilePage.clock.setFixedTime(new Date("2026-01-15T10:00:00Z"));

      // Navigate and wait
      await navigateAndWait(mobilePage, page.path, page.contentSelector);

      // Stabilize
      await stabilizeForScreenshot(mobilePage);

      // Capture mobile screenshot
      await expect(mobilePage).toHaveScreenshot(
        `${page.name}-mobile.png`,
        {
          fullPage: true,
          maxDiffPixelRatio: 0.01,
        },
      );

      await context.close();
    });
  }
});
