/**
 * PathForge — Prod Smoke 8/8: Full user-journey ping
 * =====================================================
 *
 * MPR §7 item 8: register → verify → login → upload CV → Career DNA
 * → checkout (test card) → subscription active → customer portal →
 * delete account → same-email re-register.
 *
 * Full destructive run lives in the staging gameday workflow
 * (`.github/workflows/staging-gameday.yml`).  In prod we **read-only
 * ping** the public marketing → registration handoff path so any
 * regression in /register or /login URL patterns lights up:
 *
 *   1. GET https://pathforge.eu  → 200
 *   2. GET /register             → 200 + page contains the
 *                                   registration form selector
 *   3. GET /login                → 200 + page contains the login
 *                                   form selector
 *
 * Web layer up + auth pages reachable = the journey starts.  The
 * deeper destructive items run weekly on staging.
 */

import { test, expect } from "@playwright/test";

const WEB_BASE = process.env.PROD_SMOKE_WEB_BASE_URL ?? "https://pathforge.eu";

test("marketing landing page is reachable", async ({ page }) => {
  await page.goto(WEB_BASE, { waitUntil: "domcontentloaded" });
  await expect(page).toHaveTitle(/PathForge/i);
});

test("register page renders the form", async ({ page }) => {
  await page.goto(`${WEB_BASE}/register`, { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("textbox", { name: /email/i }).first(),
  ).toBeVisible();
});

test("login page renders the form", async ({ page }) => {
  await page.goto(`${WEB_BASE}/login`, { waitUntil: "domcontentloaded" });
  await expect(
    page.getByRole("textbox", { name: /email/i }).first(),
  ).toBeVisible();
});
