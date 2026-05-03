/**
 * PathForge — Prod Smoke 7/8: Account deletion cascade
 * =======================================================
 *
 * MPR §7 item 7: `DELETE /api/v1/users/me` cascades across all user-
 * linked tables, revokes tokens, cancels Stripe subscription.
 *
 * **Read-only smoke** (production cannot tolerate deleting a fixture
 * user every 15 minutes). Asserts the route is reachable + behaves
 * idempotently against an unauthenticated request (401 expected).
 *
 * The full destructive test runs **only on staging** via a separate
 * gameday workflow; this prod-side smoke confirms the route is
 * mounted and rejects unauthenticated calls cleanly.
 */

import { test, expect } from "@playwright/test";

const API_BASE = process.env.PROD_SMOKE_API_BASE_URL ?? "https://api.pathforge.eu";

test("DELETE /users/me requires auth", async ({ request }) => {
  const resp = await request.delete(`${API_BASE}/api/v1/users/me`);
  const status = resp.status();
  const hint =
    status === 405
      ? " Status 405 means the DELETE handler is not registered on the deployed API — " +
        "redeploy apps/api so the delete_account route in apps/api/app/api/v1/users.py ships."
      : "";
  expect(
    [401, 403],
    `DELETE /users/me returned ${status}; expected 401 or 403 (unauthenticated reject).${hint}`,
  ).toContain(status);
});
