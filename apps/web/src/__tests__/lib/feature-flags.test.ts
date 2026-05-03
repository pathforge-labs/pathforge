/**
 * PathForge — feature-flags.ts tests (T5 / Sprint 57, ADR-0009)
 * ===============================================================
 *
 * Mirrors the Python tests in `apps/api/tests/test_feature_flags.py`.
 * The bucketing algorithm must produce the same answer on both sides
 * for the same `(flag_key, user_id)` so a 5%-adopter on one side is
 * also a 5%-adopter on the other.
 */

import { describe, it, expect } from "vitest";
import {
  PAYING_USER_DELAY_MS,
  isEnabled,
  type FlagDefinition,
  type FlagUser,
} from "@/lib/feature-flags";

const BASE_USER: FlagUser = { id: "user-0001", tier: "free" };
// Pinned `now` for the non-tier tests where time doesn't matter.
// `isEnabled` requires `now` explicitly (no default) so SSR callers
// must pass a deterministic timestamp; tests follow the same contract.
const NOW = 1_710_000_000_000;

describe("isEnabled — internal_only stage", () => {
  it("returns true for internal users", () => {
    const flag: FlagDefinition = { stage: "internal_only" };
    expect(isEnabled("x", flag, { ...BASE_USER, is_internal: true }, NOW)).toBe(true);
  });

  it("returns false for external users", () => {
    const flag: FlagDefinition = { stage: "internal_only" };
    expect(isEnabled("x", flag, BASE_USER, NOW)).toBe(false);
  });
});

describe("isEnabled — percent stages", () => {
  it("user bucketing is deterministic", () => {
    const flag: FlagDefinition = { stage: "percent_5" };
    const a = isEnabled("flag-x", flag, { id: "u-stable" }, NOW);
    const b = isEnabled("flag-x", flag, { id: "u-stable" }, NOW);
    expect(a).toBe(b);
  });

  it("5%-adopters are subset of 25%-adopters", () => {
    const users: FlagUser[] = Array.from({ length: 1_000 }, (_, i) => ({
      id: `user-${String(i).padStart(4, "0")}`,
    }));
    const flag5: FlagDefinition = { stage: "percent_5" };
    const flag25: FlagDefinition = { stage: "percent_25" };
    const enabledAt5 = new Set(
      users.filter((u) => isEnabled("flag-x", flag5, u, NOW)).map((u) => u.id),
    );
    const enabledAt25 = new Set(
      users.filter((u) => isEnabled("flag-x", flag25, u, NOW)).map((u) => u.id),
    );
    for (const id of enabledAt5) {
      expect(enabledAt25.has(id)).toBe(true);
    }
  });

  it("100% covers everyone (non-major-release path)", () => {
    const flag: FlagDefinition = { stage: "percent_100" };
    for (let i = 0; i < 50; i++) {
      expect(isEnabled("flag-x", flag, { id: `u-${i}` }, NOW)).toBe(true);
    }
  });
});

describe("isEnabled — tier-aware canary", () => {
  it("paying users are held back during 24h on major releases", () => {
    const startedAt = new Date(NOW - 2 * 60 * 60 * 1_000).toISOString();
    const flag: FlagDefinition = {
      stage: "percent_100",
      major_release: true,
      rollout_started_at: startedAt,
    };
    const paying: FlagUser = { id: "paying-1", tier: "premium" };
    expect(isEnabled("engine-v2", flag, paying, NOW)).toBe(false);
  });

  it("paying users unblocked after 24h", () => {
    const startedAt = new Date(
      NOW - PAYING_USER_DELAY_MS - 60 * 1000,
    ).toISOString();
    const flag: FlagDefinition = {
      stage: "percent_100",
      major_release: true,
      rollout_started_at: startedAt,
    };
    const paying: FlagUser = { id: "paying-2", tier: "premium" };
    expect(isEnabled("engine-v2", flag, paying, NOW)).toBe(true);
  });

  it("minor releases never gate paying users", () => {
    const startedAt = new Date(NOW - 60 * 1000).toISOString();
    const flag: FlagDefinition = {
      stage: "percent_100",
      major_release: false,
      rollout_started_at: startedAt,
    };
    const paying: FlagUser = { id: "paying-3", tier: "pro" };
    expect(isEnabled("patch-x", flag, paying, NOW)).toBe(true);
  });
});

describe("isEnabled — fail-closed", () => {
  it("unknown flag returns false", () => {
    expect(isEnabled("missing", null, BASE_USER, NOW)).toBe(false);
    expect(isEnabled("missing", undefined, BASE_USER, NOW)).toBe(false);
  });

  it("missing user id returns false", () => {
    const flag: FlagDefinition = { stage: "percent_100" };
    expect(isEnabled("x", flag, { id: "" }, NOW)).toBe(false);
  });
});
