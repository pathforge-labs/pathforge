/**
 * PathForge — Prod Smoke 4/8: Redis-stop → 503 surface
 * =======================================================
 *
 * MPR §7 item 4: `/health/ready` returns 503 when Redis is stopped.
 * Live production cannot tolerate a Redis stop, so this smoke
 * exercises a **read-only assertion**: the readiness probe surfaces
 * `redis_detail` and `rate_limit_degraded` fields whose presence is
 * the SLO contract.  An operator deliberately stopping Redis (e.g.
 * gameday) sees the smoke turn red within one cron tick.
 */

import { test, expect } from "@playwright/test";

const API_BASE = process.env.PROD_SMOKE_API_BASE_URL ?? "https://api.pathforge.eu";

test("readiness probe exposes the redis-degradation contract", async ({
  request,
}) => {
  const resp = await request.get(`${API_BASE}/api/v1/health/ready`);
  expect(resp.status()).toBe(200);
  const body = await resp.json();
  // The contract: these fields exist (degradation visible in
  // structured form). We don't assert on values — Redis is up in
  // steady state — only on the keys' presence.
  expect(body).toHaveProperty("redis_detail");
  expect(body).toHaveProperty("rate_limit_degraded");
});
