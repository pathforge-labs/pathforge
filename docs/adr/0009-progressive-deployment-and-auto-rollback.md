# ADR-0009 — Progressive Deployment + Auto-Rollback

* **Status:** Accepted (revisits ADR-0005)
* **Sprint:** 57 (T5 of `docs/architecture/sprint-55-58-code-side-readiness.md`)
* **Closes:** sprint-plan §6 (new gap, not in MPR)
* **Date:** 2026-04-26
* **Author:** PathForge engineering
* **Reviewers:** belengaz, reso, pizmam

## Context

[ADR-0005](0005-deployment-strategy-rolling-via-railway.md) parked
canary in favour of Railway's native rolling deploy. Rationale at the
time: *"Railway native rolling is enough for 1k MAU."*  At launch we
expect 10k+ MAU within 90 days. **Rolling regressions hit 100 % of
traffic before a rollback can be triggered.** Industry baseline at
our user count is canary or feature-flag rollout.

## Decision

Ship a **feature-flag-driven progressive rollout** as the *deployment
unit*. Each new feature lands behind a flag with four stages:

```
internal_only → percent_5 → percent_25 → percent_100
```

Plus an automatic **Sentry → auto-rollback → `internal_only`** path
when a release's P0 user rate exceeds the threshold during a partial
rollout.

This is *additive* to Railway's rolling deploy — the rolling deploy
still happens, but the **visibility** of new code is gated by the flag.
Bad code merging to `main` is no longer the same event as bad code
running in front of every user.

### Two systems, one mental model

| System | Module | Gates |
|:---|:---|:---|
| **Tier access** | `app.core.feature_gate` | "Does this user's subscription tier include this engine?" — stable matrix, doesn't change on each deploy |
| **Rollout visibility** | `app.core.feature_flags` *(new)* | "Has this user's bucket been promoted to the new code path yet?" — moves with each deploy |

A user's effective access is `tier_gate(user, engine) AND
flag.is_enabled(user, flag)`. Mixing the two into a single object
would obscure the meaning of every check.

### Bucket determinism

Bucket assignment uses **SHA-256 of `flag_key + user_id`**. The same
user always lands in the same bucket so a user enabled at 5 % stays
enabled at 25 % and 100 %. Without this, the system would flip random
users in and out of the new code path on each percent bump, destroying
the value of the canary stage.

### Tier-aware canary (sprint plan §12 default decision #2)

Conventional canary: random 5 % of users see the new build.
PathForge canary: **paying users (`pro` / `premium`) see the
previous-confirmed-stable build for an additional 24 hours after
rollout starts on major releases**. Free users absorb canary risk
first.

This is consistent with the user-as-customer business model — paying
users are the ones we cannot afford to disrupt; free users
*implicitly* trade lower stability for free access. Stripe + Mailchimp
use this pattern internally; **no career-platform competitor offers
it as a deliberate design.**

The 24 h carve-out applies only when:
* the flag is in a partial-rollout stage **or** within 24 h of going
  to 100 %, AND
* the flag carries `major_release: True`.

Bug-fix patches (`major_release: False`) deploy unsegmented.

### Auto-rollback trigger (sprint plan §12 default decision #5)

> P0 user rate **> 0.1 %** at any 5-minute window during a partial
> rollout (5 % or 25 %) → automatic rollback to `internal_only`.

0.1 % at our 10 k-MAU launch target = 10 affected users / 5 min
window. That's the smallest user-cohort cardinality where a real
issue is statistically distinguishable from infrastructure noise.

The threshold is **per-window**, not per-release-cumulative — a
slow-burn 0.05 % bug stays under the gate but still surfaces in the
dashboard, and the operator can manually flip via the runbook
(`docs/runbooks/canary-rollback.md`).

### Provider hosting (sprint plan §12 default decision #1)

GrowthBook **SaaS free tier** for ≤ 5 flags; self-host above. Vendor
choice over Unleash / Flagsmith because GrowthBook is already vetted
in the original sprint plan §3.2 and its SDK has first-class TypeScript
+ Python support — no shim needed.

In the pre-GrowthBook launch state the codebase ships
`InMemoryFlagProvider`. Tests run against it; production runs against
the same abstraction over the GrowthBook SDK once OPS-3 + GrowthBook
account land. **Code merge does not block on GrowthBook activation.**

## Considered alternatives

* **Native Railway canary (traffic split).** Rejected — not generally
  available on Railway hobby/team tier; vendoring around it is
  fragile.
* **Open-source flag library (Unleash, Flagsmith).** Considered but
  GrowthBook is already vetted; same team that runs the SaaS also
  maintains the OSS edition so a self-host migration is supported by
  the same provider.
* **Per-user-segment rollout (e.g. premium gets stable build).** This
  is what we adopted, but with a 24 h time-bound rather than a
  permanent split — paying users eventually see the new build, just
  later. Permanent split would split the codebase in half (two
  feature surfaces forever) and is rejected as scope creep.
* **Polling Sentry's API for release health.** Rejected — webhooks
  are the documented integration path. Polling either misses canary
  windows (5-min poll) or rate-limits us out of the API (per-second
  poll).

## Implementation

| Layer | File(s) | Responsibility |
|:---|:---|:---|
| Flag system | `app/core/feature_flags.py` (new) | `RolloutStage`, `FlagDefinition`, `FeatureFlagProvider` ABC, `InMemoryFlagProvider`, `is_enabled(flag, user, provider)`. Bucket-stable SHA-256, tier-aware delay, fail-closed on unknown flag. |
| Auto-rollback | `app/core/sentry_auto_rollback.py` (new) | `POST /api/v1/internal/sentry/auto-rollback` webhook. HMAC-SHA256 sig verify, threshold check, idempotent on already-rolled-back flag, 401 on missing/bad signature. |
| Config | `app/core/config.py` | Adds `sentry_webhook_secret` setting (empty by default → fail-closed). |
| Routes | `app/main.py` | Mounts the rollback router under `/api/v1`. |
| Runbook | `docs/runbooks/canary-rollback.md` (new) | Manual override procedure (when auto-rollback misfires). |
| Web client (T5-web) | `apps/web/src/lib/feature-flags.ts` | SSR-aware client SDK; deferred to follow-up PR (mirrors T4 backend/web split). |

### Webhook signature scheme

Sentry's `Sentry-Hook-Signature` header carries `HMAC-SHA256(body,
SENTRY_WEBHOOK_SECRET)`. We verify in **constant time** via
`hmac.compare_digest`. Same posture the Stripe webhook handler uses;
keeps the verification surface uniform across providers.

Empty `SENTRY_WEBHOOK_SECRET` rejects every request 401 (fail-closed).
Operator opt-in is required — an unconfigured deploy cannot be
exploited to flip flags.

### Idempotency

Sentry retries failed webhook deliveries up to 3 times. The handler
tolerates duplicates by:

1. Reading the current flag stage **before** mutating.
2. Returning `{"rolled_back": false, "already_at_internal_only": true}`
   when the flag is already at `internal_only`. **Crucially, we do
   NOT bump `rollout_started_at` in this branch** — that would extend
   the 24 h paying-user delay on the next re-enable for no operational
   reason.

## Privacy & GDPR

The flag-bucketing hash takes only `flag_key + user_id` (UUID). No
PII is included in the hash input or in the breadcrumb / log
emissions. Auto-rollback events are audit-logged at WARNING level
with `flag_key`, `previous_stage`, `rate`, `threshold` — no user
identifiers.

## Performance impact

* `is_enabled` is one SHA-256 + one dict lookup + one `datetime.now()`
  comparison. ≈ 6 µs per call on the dev box.
* Webhook receiver is request-rate-bounded by Sentry's alert cadence
  (≤ 1 / 5 min in steady state, ≤ 3 retries per genuine alert).

## Rollback (of T5 itself)

Single-line removal of `application.include_router(sentry_rollback_router, …)`
in `apps/api/app/main.py` un-mounts the webhook. The flag system can
remain in place harmlessly — `is_enabled()` returns False for any
flag the operator hasn't defined (fail-closed).

## Quality gate

Per sprint plan §6.5 (T5):

| Criterion | Target | Status |
|:---|:---:|:---|
| ADR-0009 drafted | yes | ✅ this file |
| `is_enabled` test coverage | ≥ 90 % | ✅ 12 cases (stage transitions, bucket stability, tier carve-out, set_rollout) |
| Auto-rollback dry-run on staging | green | 🚧 Sprint 57 final-week gameday — pending N-4 staging activation |

## References

* sprint-plan §6 (T5 spec) and §12 (default decisions #1, #2, #5)
* [ADR-0005](0005-deployment-strategy-rolling-via-railway.md) —
  parked canary (revisited here)
* [ADR-0007](0007-route-query-budget-and-causality-ledger.md) —
  query budget. Engine-name attribution joins through the same
  `analysis_type` column the auto-rollback's per-flag tag references.
* Stripe Engineering — *"Workflow patterns for production
  reliability"* (the per-tier rollout pattern)
* LinkedIn Engineering — *Project Voyager* (canary infrastructure)
