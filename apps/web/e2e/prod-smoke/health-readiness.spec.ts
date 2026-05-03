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
  const status = resp.status();
  // Read the body before asserting so failure diagnostics include the
  // probe payload regardless of which assertion fires.
  let body: Record<string, unknown> = {};
  try {
    body = (await resp.json()) as Record<string, unknown>;
  } catch {
    // Non-JSON body (e.g. gateway error page) — leave body empty; the
    // status-code assertion below will surface the raw status.
  }
  const summary = `status=${status}, body=${JSON.stringify(body)}`;
  expect(status, `readiness probe HTTP ${status}; expected 200. ${summary}`).toBe(200);
  // Backend uses "ok" in the healthy state and "unhealthy" when any
  // dependency probe fails (apps/api/app/api/v1/health.py:253). A
  // value of "degraded" means the deployed API predates that revision
  // — redeploy apps/api from main to recover the contract.
  expect(
    body.status,
    `readiness body.status=${JSON.stringify(body.status)}; expected "ok". ${summary}`,
  ).toBe("ok");
});
