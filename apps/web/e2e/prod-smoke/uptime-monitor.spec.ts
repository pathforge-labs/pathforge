/**
 * PathForge — Prod Smoke 5/8: UptimeRobot alert latency
 * =======================================================
 *
 * MPR §7 item 5: UptimeRobot alert fires within 5 min of API stop.
 * Verified by querying the UptimeRobot API for the configured
 * monitor's `interval` field — must be ≤ 300 s (5 min) so the SLA
 * the operator depends on is honoured.
 */

import { test, expect } from "@playwright/test";

const UPTIMEROBOT_API_KEY = process.env.PROD_SMOKE_UPTIMEROBOT_API_KEY;
const UPTIMEROBOT_MONITOR_NAME =
  process.env.PROD_SMOKE_UPTIMEROBOT_MONITOR_NAME ?? "pathforge-api-readiness";

test.skip(
  !UPTIMEROBOT_API_KEY,
  "UptimeRobot API key not configured — skipping prod-smoke uptime check",
);

test("uptime monitor poll interval is ≤ 5 minutes", async ({ request }) => {
  const resp = await request.post(
    "https://api.uptimerobot.com/v2/getMonitors",
    {
      form: {
        api_key: UPTIMEROBOT_API_KEY ?? "",
        format: "json",
      },
    },
  );
  expect(resp.status()).toBe(200);
  const body = await resp.json();
  expect(body.stat).toBe("ok");
  type Monitor = {
    friendly_name: string;
    interval: number;
    status: number;
  };
  const monitors = (body.monitors ?? []) as Monitor[];
  const target = monitors.find(
    (m) => m.friendly_name === UPTIMEROBOT_MONITOR_NAME,
  );
  expect(target, "monitor not configured").toBeTruthy();
  expect(target!.interval).toBeLessThanOrEqual(300);
  // Also assert the monitor is up (status=2) right now; status=9
  // means down, status=8 means seems-down.
  expect(target!.status).toBe(2);
});
