/**
 * PathForge — Prod Smoke 1/8: Health readiness
 * ==============================================
 *
 * MPR §7 item 1: `curl /api/v1/health/ready` → 200 with DB+Redis+
 * rate-limit OK.  Ran every 15 minutes against
 * https://api.pathforge.eu so any TLS / DB / Redis regression in
 * production lights up Sentry within one cron tick.
 *
 * The smoke does **not** assert on internal field shapes beyond the
 * top-level boolean — those change with internal hardening
 * (ADR-0001 / ADR-0002 added structured `db` / `redis_detail`
 * blocks).  We pin the contract that protects the synthetic monitor
 * and let the rest evolve.
 */

import { test, expect } from "@playwright/test";

const API_BASE = process.env.PROD_SMOKE_API_BASE_URL ?? "https://api.pathforge.eu";

test("api health readiness returns 200 + status ok", async ({ request }) => {
  const resp = await request.get(`${API_BASE}/api/v1/health/ready`);
  expect(resp.status()).toBe(200);
  const body = await resp.json();
  expect(body.status).toBe("ok");
});
