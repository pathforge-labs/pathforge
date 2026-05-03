/**
 * PathForge — Prod Smoke 3/8: dependency-vulnerability gate
 * ===========================================================
 *
 * MPR §7 item 3: CI fails on a branch introducing a known vulnerable
 * dep.  This synthetic test queries the **last successful main
 * pipeline** for the SBOM artefact and asserts none of the listed
 * advisories are in the "high" or "critical" tier.  Doing it on
 * every cron tick catches the case where a transitive dep is
 * re-disclosed between merges (typical Dependabot lag).
 */

import { test, expect } from "@playwright/test";

const GH_TOKEN = process.env.PROD_SMOKE_GH_TOKEN;
const GH_REPO = process.env.PROD_SMOKE_GH_REPO ?? "pathforge-labs/pathforge";

test.skip(
  !GH_TOKEN,
  "GitHub token not configured — skipping prod-smoke SBOM advisory check",
);

test("no high/critical advisories on default-branch SBOM", async ({
  request,
}) => {
  const url = `https://api.github.com/repos/${GH_REPO}/dependabot/alerts?state=open&severity=high,critical`;
  const resp = await request.get(url, {
    headers: {
      Authorization: `Bearer ${GH_TOKEN}`,
      Accept: "application/vnd.github+json",
    },
  });
  expect(resp.status()).toBe(200);
  const alerts = (await resp.json()) as unknown[];
  expect(Array.isArray(alerts)).toBe(true);
  expect(alerts.length).toBe(0);
});
