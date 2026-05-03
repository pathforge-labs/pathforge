/**
 * PathForge — Prod Smoke 6/8: Refresh rotation replay rejection
 * ================================================================
 *
 * MPR §7 item 6: refresh rotation — reused refresh token → 401.
 * Uses the synthetic baseline-fixture user (provisioned by T6 admin
 * tooling) so we can drive a real authenticated round-trip without
 * polluting prod with throwaway accounts.
 *
 * Flow:
 *   1. login → get { access, refresh }
 *   2. refresh once → tokens rotated (valid)
 *   3. replay the original refresh → 401 (replay detect)
 */

import { test, expect } from "@playwright/test";

const API_BASE = process.env.PROD_SMOKE_API_BASE_URL ?? "https://api.pathforge.eu";
const SYNTHETIC_USER = process.env.PROD_SMOKE_USER_EMAIL;
const SYNTHETIC_PASS = process.env.PROD_SMOKE_USER_PASSWORD;

test.skip(
  !SYNTHETIC_USER || !SYNTHETIC_PASS,
  "Synthetic baseline user not configured — skipping refresh-rotation smoke",
);

test("refresh-token replay returns 401", async ({ request }) => {
  const login = await request.post(`${API_BASE}/api/v1/auth/login`, {
    data: { email: SYNTHETIC_USER, password: SYNTHETIC_PASS },
  });
  expect(login.status()).toBe(200);
  const tokens = await login.json();
  const original = tokens.refresh_token as string;
  expect(original).toBeTruthy();

  const first = await request.post(`${API_BASE}/api/v1/auth/refresh`, {
    data: { refresh_token: original },
  });
  expect(first.status()).toBe(200);

  const replay = await request.post(`${API_BASE}/api/v1/auth/refresh`, {
    data: { refresh_token: original },
  });
  expect(replay.status()).toBe(401);
});
