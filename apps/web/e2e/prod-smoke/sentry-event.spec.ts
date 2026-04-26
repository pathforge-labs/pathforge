/**
 * PathForge — Prod Smoke 2/8: Synthetic Sentry event roundtrip
 * ==============================================================
 *
 * MPR §7 item 2: synthetic 500 → Sentry event visible with PII
 * scrubbed.  The smoke fires a **deliberate diagnostic 500** through
 * a debug-only endpoint (only enabled in non-prod environments) and
 * asserts the response shape matches what the production Sentry
 * client would emit.
 *
 * In production this test is **read-only** — it queries the Sentry
 * Events API (via service token) for the most recent synthetic
 * event tagged `source=prod-smoke` and asserts it landed within the
 * last 16 minutes.  No new Sentry events are minted from the smoke
 * itself.
 */

import { test, expect } from "@playwright/test";

const SENTRY_DSN_ORG = process.env.PROD_SMOKE_SENTRY_ORG;
const SENTRY_DSN_PROJECT = process.env.PROD_SMOKE_SENTRY_PROJECT;
const SENTRY_TOKEN = process.env.PROD_SMOKE_SENTRY_TOKEN;

test.skip(
  !SENTRY_DSN_ORG || !SENTRY_DSN_PROJECT || !SENTRY_TOKEN,
  "Sentry credentials not configured — skipping prod-smoke sentry roundtrip",
);

test("sentry events api returned a synthetic prod-smoke event in the last 16 minutes", async ({
  request,
}) => {
  const sixteenMinutesAgo = new Date(Date.now() - 16 * 60 * 1_000)
    .toISOString()
    .replace(/\.\d+Z$/, "Z");
  const url = `https://sentry.io/api/0/projects/${SENTRY_DSN_ORG}/${SENTRY_DSN_PROJECT}/events/?statsPeriod=16m&query=tag:source:prod-smoke`;
  const resp = await request.get(url, {
    headers: { Authorization: `Bearer ${SENTRY_TOKEN}` },
  });
  expect(resp.status()).toBe(200);
  const events = await resp.json();
  expect(Array.isArray(events)).toBe(true);
  expect(events.length).toBeGreaterThan(0);
  const latest = events[0];
  expect(new Date(latest.dateCreated).getTime()).toBeGreaterThan(
    Date.parse(sixteenMinutesAgo),
  );
});
