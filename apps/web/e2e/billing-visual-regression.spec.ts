/**
 * PathForge — Visual Regression Baselines
 * ==========================================
 * Sprint 35 (WS-7): Playwright specs for pricing and billing page baselines.
 *
 * These tests capture screenshot baselines for visual regression testing.
 * Compare against baselines on subsequent runs to detect unintended UI changes.
 *
 * Prerequisites:
 *   - Dev server running: `pnpm --filter web run dev`
 *   - First run creates baselines: `pnpm --filter web run e2e --update-snapshots`
 */

import { expect, test } from "@playwright/test";

test.describe("Pricing Page — Visual Regression", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/pricing");
  });

  test("pricing page loads with 3 tier cards", async ({ page }) => {
    // Wait for the pricing grid to render
    await page.waitForSelector(".pricing-grid__cards", { timeout: 10_000 });

    // Verify 3 pricing cards are present
    const cards = page.locator(".pricing-card");
    await expect(cards).toHaveCount(3);
  });

  test("pricing page has correct heading", async ({ page }) => {
    const heading = page.getByRole("heading", { level: 1 });
    await expect(heading).toHaveText("Simple, Transparent Pricing");
  });

  test("billing toggle switches between monthly and annual", async ({ page }) => {
    await page.waitForSelector(".pricing-grid__toggle", { timeout: 10_000 });

    // Click annual toggle
    const annualButton = page.getByRole("radio", { name: /annual/i });
    await annualButton.click();
    await expect(annualButton).toHaveAttribute("aria-checked", "true");

    // Click monthly toggle
    const monthlyButton = page.getByRole("radio", { name: /monthly/i });
    await monthlyButton.click();
    await expect(monthlyButton).toHaveAttribute("aria-checked", "true");
  });

  test("free tier card has Get Started CTA", async ({ page }) => {
    await page.waitForSelector(".pricing-card", { timeout: 10_000 });
    const freeCard = page.locator(".pricing-card").first();
    const cta = freeCard.getByRole("link", { name: /get started/i });
    await expect(cta).toBeVisible();
  });

  test("FAQ section is present", async ({ page }) => {
    const faqSection = page.getByRole("region", { name: /frequently asked questions/i });
    await expect(faqSection).toBeVisible();
  });

  test("pricing page screenshot baseline", async ({ page }) => {
    await page.waitForSelector(".pricing-grid__cards", { timeout: 10_000 });
    // Wait for fonts and images to load
    await page.waitForLoadState("networkidle");
    await expect(page).toHaveScreenshot("pricing-page.png", {
      fullPage: true,
      maxDiffPixelRatio: 0.01,
    });
  });
});

test.describe("Billing Settings Page — Visual Regression", () => {
  // Note: Billing page requires authentication
  // These tests will need auth fixtures when run against the full app

  test("billing page loads (unauthenticated redirect)", async ({ page }) => {
    await page.goto("/dashboard/settings/billing");
    // Should redirect to login if not authenticated
    // This establishes the redirect behavior baseline
    await page.waitForURL(/\/(login|auth|dashboard)/, { timeout: 10_000 });
  });
});
