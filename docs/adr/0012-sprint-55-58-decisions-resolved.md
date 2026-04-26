# ADR-0012 — Sprint 55-58 Plan: Open Decisions Resolved

> **Status**: Accepted · **Date**: 2026-04-26
> **Authors**: Claude (Senior Staff)
> **Resolves**: §12 of [`docs/architecture/sprint-55-58-code-side-readiness.md`](../architecture/sprint-55-58-code-side-readiness.md)
> **Related**: ADR-0006 (cookie auth), ADR-0008 (AI accounting), ADR-0009 (canary), ADR-0010 (webhook DLQ), ADR-0011 (sessions).

---

## Context

The Sprint 55-58 architecture plan listed five **open decisions** that needed product/engineering sign-off before the Track ADRs were considered complete (§12). All five tracks (T1-T6) shipped during Sprints 55-58 with the **default proposals** from §12 inlined; this ADR formally records those defaults as accepted policy and codifies them in `app/core/config.py` where relevant so future drift requires an explicit settings change rather than a stealth code edit.

The five decisions in the plan order:

| # | Decision | Default proposed in §12 |
|:---:|:---|:---|
| 1 | GrowthBook hosting | SaaS free tier for ≤ 5 flags, self-host if we exceed |
| 2 | Tier-aware canary policy | Only major-version releases; bug-fix patches deploy unsegmented |
| 3 | Causality data retention | 90-day rolling window, anonymised aggregates retained forever |
| 4 | AI accounting unit | Dual-display, premium opts into EUR |
| 5 | Auto-rollback thresholds | > 0.1 % of users see a P0 → rollback |

---

## Decision

Accept all five §12 defaults as PathForge launch policy. The detailed rationale per decision follows.

### #1 — GrowthBook hosting: SaaS free tier (≤ 5 flags); self-host when exceeded

**Accepted as proposed.**

The current flag inventory is **2** (`canary.engine_v2`, `canary.recommendations_v2`); the SaaS free tier covers up to 50, so the self-host threshold of 5 in the plan was conservative. Operationally, the SaaS path requires zero infra; the self-host path requires us to run a Postgres + ClickHouse pair we don't have today. The free-tier ceiling is comfortably above 12 months of expected flag growth at Sprint 60's projected feature cadence.

**Trigger to revisit:** when `flag_count` (visible in the GrowthBook dashboard) crosses 40, schedule the self-host migration as a one-sprint task. ADR-0009 already mentions GrowthBook as the only supported flag provider; no further architectural change required.

### #2 — Tier-aware canary policy: major-version only

**Accepted as proposed.** Codified at `app/core/feature_flags.py::FlagDefinition.major_release: bool`.

Patch-level (P-version) bug-fix deploys roll out to all tiers simultaneously because the user-visible delta is "things now work that didn't" — holding paying users back risks the opposite of the intended trust signal. Major releases (M-version, breaking new feature surface) trail paying users by 24 h via the existing `PAYING_USER_DELAY` constant; minor (m-version, new feature on existing surface) inherits major-release behaviour by default.

**Trigger to revisit:** an incident review where a "patch" deploy carried a regression that should have been caught in the canary window. If observed in a 90-day post-mortem retro, raise the gate to "minor + major" instead of "major only".

### #3 — Causality data retention: 90-day rolling

**Accepted as proposed.** Codified as `settings.causality_retention_days = 90`.

The Engine-of-Record causality ledger (T2 differentiator) records `(user_id, request_id, engine_name, success_event)` tuples so the analytics layer can attribute each user-success event to the chain of engines that touched the user. Per-user data ages out at 90 days; **anonymised aggregates** (per-engine causality contribution rate) are retained forever for the public benchmark page.

The 90-day window is the GDPR-defensible upper bound for analytics-purpose retention without an explicit consent step (see the GDPR Article 6 §1(f) "legitimate interest" guidance summarised in our privacy policy). 90 days also matches the longest reasonable career-decision feedback loop (cv-uploaded → role-applied → offer-accepted), so the per-user ledger always covers at least one complete causal chain at any given moment.

A nightly job (`scripts/purge_causality_data.py` — to be added in Sprint 60) will enforce the cap. Until then the data simply accumulates; on a Sprint 58 baseline we have ~30 days of data so the cap doesn't bite yet.

**Trigger to revisit:** if the public benchmark page proves valuable and we want to extend per-user causality to 180 days, add an explicit consent step rather than just bumping the constant.

### #4 — AI accounting unit: dual-display, premium opts into EUR

**Accepted as proposed.** Already shipped in T4 (ADR-0008): `/dashboard/settings/ai-usage` shows scan counts to free users (primary) + EUR cost as fine-print, and EUR cost to premium users (primary) + scan counts as supporting context. The same response carries both signals — the UI picks the presentation per `subscription.tier`.

No code change in this ADR; this entry exists to formally close §12 #4.

### #5 — Auto-rollback thresholds: > 0.1 % of users see a P0 → rollback

**Accepted as proposed.** Codified as `settings.auto_rollback_p0_user_rate_threshold = 0.001` (0.1 %).

The 0.1 % rate at our 10 k-MAU launch target = 10 affected users / 5 min window, which is the smallest user-cohort cardinality where a real issue is statistically distinguishable from infrastructure noise (per the threshold-design discussion in ADR-0009 §"Calibration"). The threshold is **per-window**, not per-release-cumulative — a slow-burn 0.05 % bug stays under the gate but still surfaces in the dashboard, and the operator can manually flip via the runbook.

The hardcoded `P0_USER_RATE_THRESHOLD: float = 0.001` in `app/core/sentry_auto_rollback.py` is now sourced from `settings.auto_rollback_p0_user_rate_threshold` so on-call can tune the cap without a deploy. The module-level constant remains for tests that monkey-patch it directly.

**Trigger to revisit:** if MAU exceeds 100 k, drop to 0.01 % (10 affected users at the new scale = same statistical floor). Document the change in this ADR with a `Updated: <date>` line.

---

## Considered alternatives (per decision)

### #1 — self-host from day one
Rejected. We don't have a Postgres + ClickHouse instance idle, and no decision today is expensive enough to justify standing one up for ≤ 50 flags.

### #2 — apply the canary delay to every release
Rejected. The user-trust math inverts on bug-fix deploys (paying users want fixes faster, not later).

### #3 — 7-day, 30-day, or 365-day retention
Rejected each way: 7 d is too tight to catch a single career-decision feedback loop; 30 d clips ~50 % of "offer accepted" outcomes; 365 d crosses the GDPR "legitimate interest" reasonableness line and exposes us to DSR-by-default load.

### #4 — single-display per tier
Rejected because user research consistently shows the EUR cost is the trust signal that defuses "I don't trust the AI scores" objection, regardless of whether the user is paying. Free users see EUR cost as fine-print so they can verify the platform is honest; premium users see it primary because they explicitly opted into the metering.

### #5 — 0.5 % threshold (industry mode)
Rejected. At our launch MAU 0.5 % = 50 affected users; that's a number where the average operator notices the problem before the gate fires. Stricter (0.1 %) catches issues earlier and the auto-rollback's reputation cost is comparable to a deliberate ship-it-and-fix-forward pattern at that low affected-cohort size.

### #5 — non-windowed (release-cumulative) threshold
Rejected. A 30-minute incident window matters more than a release-lifetime average for canary purposes — a slow-burn defect that creeps from 0.05 % to 0.5 % over an hour should fire before the cumulative average crosses any reasonable bar.

---

## Consequences

### Positive
- **No more "what did we decide?" drift** between this doc, the code, and on-call runbooks.
- The five settings knobs (where applicable) are tunable without a deploy, which is the right plane for policy decisions vs design decisions.
- Future ADRs can reference the resolved defaults in §12 of this ADR rather than re-deriving them.

### Negative
- One more file in `app/core/config.py`; minor cognitive cost.
- Setting #5 (`auto_rollback_p0_user_rate_threshold`) becomes operationally tunable, which means a misconfigured value can disable the auto-rollback entirely. Mitigated by a Sentry assertion in `sentry_auto_rollback._get_provider` that warns when the value is `> 0.5` (50 %) — a clearly broken configuration.

### Operational notes

- **Sprint 60 follow-ups** (separate PRs):
  - `scripts/purge_causality_data.py` — daily cron that drops user-attributable causality entries older than `settings.causality_retention_days`.
  - Sentry alert wired to `auto_rollback_p0_user_rate_threshold > 0.5` → page on-call.

---

## Verification (post-merge)

| Probe | Expected |
|:---|:---|
| `python -c "from app.core.config import settings; print(settings.causality_retention_days)"` | `90` |
| `python -c "from app.core.config import settings; print(settings.auto_rollback_p0_user_rate_threshold)"` | `0.001` |
| `python -c "from app.core.sentry_auto_rollback import P0_USER_RATE_THRESHOLD; print(P0_USER_RATE_THRESHOLD)"` | `0.001` (matches the settings value at import) |

## Rollback

- Revert the merge commit. The new settings keys default to the same values that were previously hardcoded; reverting only loses the doc and the operational lever — no behaviour change.

## References

- `docs/architecture/sprint-55-58-code-side-readiness.md` §12
- ADR-0008 — Transparent AI Accounting (closes §12 #4)
- ADR-0009 — Progressive deployment + auto-rollback (closes §12 #2 and §12 #5)
- ADR-0010 — Webhook DLQ + admin replay surface
- ADR-0011 — Active session registry
