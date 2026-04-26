/**
 * PathForge — Feature Flag Client SDK (T5 / Sprint 57, ADR-0009)
 * ================================================================
 *
 * Mirrors `app/core/feature_flags.py` so the same flag can be
 * consulted server-side (Python) and client-side (TypeScript)
 * without drift.
 *
 * Stages: `internal_only` → `percent_5` → `percent_25`
 *         → `percent_100`.
 *
 * Bucketing
 * ---------
 *
 * Identical algorithm to the Python side: SHA-256 of
 * `flag_key|user_id`, take the first 8 bytes as a big-endian
 * unsigned integer, modulo 100.  A user that adopted at 5% in the
 * Python is_enabled() lands in the same bucket here.
 *
 * Tier-aware canary (default decision #2)
 * ---------------------------------------
 *
 * On major releases, paying users (`tier in {"pro", "premium"}`)
 * trail the rollout by 24 hours.  The 24 h carve-out applies when:
 *
 *   - flag stage is `percent_5` / `percent_25`, **or** within
 *     24 h of going to `percent_100`,
 *   - AND `flag.major_release === true`,
 *   - AND `user.tier` is in PAYING_TIERS.
 *
 * SSR safety
 * ----------
 *
 * All branching is **synchronous + pure** so the server-rendered
 * markup matches the client-rendered markup byte-for-byte.  No
 * `Date.now()` calls inside `isEnabled` directly (we accept the
 * current timestamp as an argument so deterministic SSR is
 * possible).
 */

/** Web Crypto SubtleCrypto SHA-256 wrapper.  Synchronous when run on
 * the server (Node 20+ exposes `crypto.subtle`), async when run in
 * the browser.  We use the **synchronous** node:crypto path on the
 * server so SSR can compute the bucket without a microtask hop.
 *
 * The fallback path (browser) uses `crypto.subtle.digest` which is
 * async; isEnabled() therefore exposes both `isEnabled` (sync,
 * server-safe) and `isEnabledAsync` (browser).  In practice, the
 * browser-side flag check happens after hydration during a client
 * component render — async there is fine.
 */

export const PAYING_TIERS = new Set<string>(["pro", "premium"]);
export const PAYING_USER_DELAY_MS = 24 * 60 * 60 * 1_000;

export type RolloutStage =
  | "internal_only"
  | "percent_5"
  | "percent_25"
  | "percent_100";

export interface FlagDefinition {
  stage: RolloutStage;
  major_release?: boolean;
  /** ISO 8601 UTC. */
  rollout_started_at?: string;
}

export interface FlagUser {
  id: string;
  tier?: string;
  is_internal?: boolean;
}

const STAGE_PERCENT: Record<RolloutStage, number> = {
  internal_only: 0,
  percent_5: 5,
  percent_25: 25,
  percent_100: 100,
};

/**
 * Synchronous bucket computation using node:crypto on the server.
 * Throws if used in a context where `node:crypto` isn't available
 * (i.e. the browser); callers that need browser-side bucketing
 * should use `bucketForAsync`.
 */
function bucketForSync(flagKey: string, userId: string): number {
  // Defer the import so a browser bundle that imports this module
  // for `isEnabledAsync` doesn't try to resolve `node:crypto`.
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { createHash } = require("node:crypto") as typeof import("node:crypto");
  const digest = createHash("sha256")
    .update(`${flagKey}|${userId}`)
    .digest();
  // Same big-endian-first-8-bytes-mod-100 as the Python side.
  const high = digest.readBigUInt64BE(0);
  return Number(high % BigInt(100));
}

async function bucketForAsync(flagKey: string, userId: string): Promise<number> {
  const encoder = new TextEncoder();
  const data = encoder.encode(`${flagKey}|${userId}`);
  const digestBuf = await crypto.subtle.digest("SHA-256", data);
  const view = new DataView(digestBuf);
  const high = view.getBigUint64(0, false);
  return Number(high % BigInt(100));
}

function passesTierCanary(
  flag: FlagDefinition,
  user: FlagUser,
  now: number,
): boolean {
  if (!flag.major_release) return true;
  const tier = user.tier ?? "free";
  if (!PAYING_TIERS.has(tier)) return true;
  if (!flag.rollout_started_at) return true;
  const startedMs = Date.parse(flag.rollout_started_at);
  if (Number.isNaN(startedMs)) return true;
  const elapsed = now - startedMs;
  return elapsed >= PAYING_USER_DELAY_MS;
}

/**
 * Server-side flag check.  Synchronous; safe for SSR + RSC code
 * paths.  Pass `now` explicitly so the caller can pin it to the
 * request timestamp for deterministic markup.
 *
 * Returns `false` for unknown flags (fail-closed) and missing
 * user IDs.
 */
export function isEnabled(
  flagKey: string,
  flag: FlagDefinition | null | undefined,
  user: FlagUser,
  now: number = Date.now(),
): boolean {
  if (!flag) return false;
  if (user.is_internal) return true;
  if (!user.id) return false;

  if (flag.stage === "internal_only") return false;
  if (flag.stage === "percent_100") {
    return passesTierCanary(flag, user, now);
  }

  const bucket = bucketForSync(flagKey, user.id);
  if (bucket >= STAGE_PERCENT[flag.stage]) return false;
  return passesTierCanary(flag, user, now);
}

/**
 * Browser-side flag check.  Uses Web Crypto's async `subtle.digest`
 * since browsers don't expose a synchronous SHA-256.  Same return
 * semantics as `isEnabled`.
 */
export async function isEnabledAsync(
  flagKey: string,
  flag: FlagDefinition | null | undefined,
  user: FlagUser,
  now: number = Date.now(),
): Promise<boolean> {
  if (!flag) return false;
  if (user.is_internal) return true;
  if (!user.id) return false;

  if (flag.stage === "internal_only") return false;
  if (flag.stage === "percent_100") {
    return passesTierCanary(flag, user, now);
  }

  const bucket = await bucketForAsync(flagKey, user.id);
  if (bucket >= STAGE_PERCENT[flag.stage]) return false;
  return passesTierCanary(flag, user, now);
}
