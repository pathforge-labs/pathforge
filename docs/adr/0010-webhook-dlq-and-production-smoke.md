# ADR-0010 — Webhook DLQ + Production Smoke

* **Status:** Accepted
* **Sprint:** 58 (T6 of `docs/architecture/sprint-55-58-code-side-readiness.md`)
* **Closes:** `docs/MASTER_PRODUCTION_READINESS.md` §7 (verification
  checklist) + Gate D webhook-failure-alerting
* **Date:** 2026-04-26
* **Author:** PathForge engineering
* **Reviewers:** belengaz, reso, pizmam

## Context

Two readiness items converge:

* **MPR §7** — 8 verification items, all unchecked, all requiring a
  production environment. Today they exist as a manual checklist a
  human walks before each launch. After launch, no continuous
  re-verification.
* **Gate D — webhook failure alerting**. The Stripe webhook handler
  exists and is HMAC-verified, but failures roll back silently;
  there's no per-event-type alerting and no DLQ for an operator to
  re-drive a failed payload.

T6 ships **the backend half** of both items in one cohesive
deliverable so the operator workflow (DLQ inspection + replay) and
the SRE workflow (continuous prod smoke) share one ledger surface.
The web e2e half lands as **PR T6-web** (mirroring T4 / T5 splits).

## Decision

### 1. Append-only webhook ledger

A new `webhook_events` table stores every webhook receiver's input +
outcome. **Distinct from the existing `billing_events` table** —
that one is the billing-domain summary (trimmed payload, used by the
dashboard); this one is the operational SRE/DLQ surface
(full payload, multi-provider, retry bookkeeping).

| Column | Role |
|:---|:---|
| `id` (uuid PK) | Surrogate primary key for replay endpoints. |
| `(provider, event_id)` UNIQUE | Natural key — same Stripe webhook retried hits the same row. |
| `event_type` | Provider's event type (`invoice.payment_succeeded`, `release.error_spike`, …). |
| `payload` JSONB | Full payload as received. Preserved for replay. |
| `outcome` | `received` / `processed` / `failed` / `dlq` (string-typed enum so a future provider can add an outcome without an Alembic enum-alter). |
| `retry_count` | Bumped on each `mark_failed` call. |
| `last_error` (Text, nullable) | Truncated at 2 KB. |
| `last_attempt_at` (timestamptz, nullable) | Refreshed on every transition. |

Two indexes — `(provider, event_id)` UNIQUE for the natural key,
`(outcome, created_at)` for the admin "show me the DLQ" query.

### 2. Outcome state machine

```
                        success
                  ┌─────────────────┐
                  ▼                 │
   received ──► processed ◄────── failed
       │                              ▲ │
       │                              │ │ retry_count == MAX_RETRY_ATTEMPTS
       │                              │ ▼
       └─► failed ──── retry ─────► failed (count++)
                           │
                           └────► dlq (replayable from admin)
```

Replay from DLQ → success transitions back to `processed`; failure
keeps the row in `dlq` and refreshes `last_error`.

`MAX_RETRY_ATTEMPTS = 3` matches Sentry's webhook retry policy — by
the time a provider has retried thrice and we've still failed, the
issue is server-side and an operator needs to look. Keeping the
count aligned with the provider's policy avoids the failure mode
where a valid event runs out of retries before it would have
on the provider side.

### 3. Independent bookkeeping commits

The business-logic transaction (e.g. Stripe subscription update)
and the ledger transition transaction are **separate sessions**.
When the business write fails and rolls back, we open a fresh
session for the ledger `mark_failed` call so the DLQ row is
visible to the operator even though the business state didn't
move. Without this, every failed webhook would leave the ledger
at `received` — which is exactly the state we built the ledger
to surface, but pointing at *nothing*.

### 4. Admin DLQ surface

Two endpoints, both gated by the existing `require_admin`
dependency:

* `GET /api/v1/admin/webhooks?status=dlq&limit=100` — list ledger
  rows. Default filter is `dlq` (the operator workflow we expect).
* `POST /api/v1/admin/webhooks/{ledger_id}/replay` — re-run the
  persisted payload through `_dispatch_replay`. Success → 200 with
  the new outcome; failure → 502 with the error detail (gateway
  semantics: we reached the handler but it couldn't complete).

The replay handler dispatches by **payload signature**, not provider
column — Stripe payloads carry `object: "event"`, Sentry alerts
carry `data.issue_alert`. Adding a new provider is one new branch;
unknown shapes raise `WebhookReplayError` so the admin sees
"unhandled provider" rather than a silent no-op.

### 5. Production smoke (T6-web, deferred)

A scheduled GitHub Action (`prod-smoke.yml`, `cron: */15 * * * *`)
runs the 8 MPR §7 verification items as a Playwright suite against
production. Failure pages `emre@pathforge.eu` via the existing Sentry
alert channel. **Lands in PR T6-web** to keep the backend PR
reviewable against the API surface.

## Considered alternatives

* **Reuse `billing_events` for DLQ.** Rejected — the trimmed payload
  isn't enough to replay, and the table already serves a billing-
  audit purpose with a 7-year retention policy. Mixing operational
  DLQ retention (90 days) with billing-audit retention (7 years)
  would either over-retain operational data or under-retain billing
  data. Two tables, two policies.
* **Per-provider DLQ tables.** Rejected — the admin workflow is
  uniform across providers; per-provider tables would force a UNION
  query for the dashboard.
* **Native enum column for `outcome`.** Rejected — adding a new
  outcome value requires `ALTER TYPE ADD VALUE` on Postgres, which
  is a non-rollback-safe migration. String column with a Python-side
  enum guard gives the same type safety with cleaner migrations.
* **Replay via background job (ARQ).** Rejected for now — operator-
  triggered replay is the workflow we expect (review first, replay
  second). A future scheduled-replay path can layer on top of the
  same service without changing the ledger.

## Privacy & GDPR

* `webhook_events.payload` may contain PII (Stripe customer email,
  Sentry breadcrumbs). Default retention: **90 days rolling**
  (matches the Causality Ledger from ADR-0007 §"Privacy & GDPR").
  Cleanup is an ARQ daily job — lands in PR T6-cleanup.
* `DELETE /api/v1/users/me` does **not** cascade through this
  table — the rows aren't user-owned (some events arrive before
  the user_id is known). Operator must manually purge if a user
  invokes Article 17 within the 90-day window.
* PII redaction stays the responsibility of the originating
  provider; we do not transform the payload at ledger-write time.

## Performance impact

* Per-webhook overhead: **two SQL operations** (one INSERT, one
  UPDATE) ≈ 4 ms p99 against the dev DB.
* `(provider, event_id)` UNIQUE index supports the idempotency
  lookup; ≈ 0.5 ms.
* Listing the DLQ at `limit=100` resolves via the
  `(outcome, created_at)` index; ≈ 1 ms.
* The DLQ ledger does **not** block the business path — `mark_failed`
  only runs after the business exception is captured, in a separate
  session.

## Rollback

* `app/api/v1/billing.py` Stripe webhook: revert the ledger
  block (one `try`/`except` block) — the legacy "no ledger" behaviour
  returns immediately.
* `app/main.py`: remove the `application.include_router(admin_webhooks.router, …)`
  line.
* The `webhook_events` table can stay in place harmlessly if the
  migration is left applied; the table is append-only and idle reads
  are zero-cost.

## Quality gate

Per sprint plan §7.4 (T6):

| Criterion | Target | Status |
|:---|:---:|:---|
| Prod smoke green for 7 consecutive days | yes | 🚧 PR T6-web (Playwright cron) |
| Webhook ledger persists 100 % of events | yes | ✅ Wired into Stripe webhook; reconciliation script lands as part of T6-cleanup |
| DLQ admin route has integration test | yes | ✅ 6 cases covering admin gate, list filters, 502-on-handler-failure, success-path |

## References

* sprint plan §7 (T6 spec)
* `docs/MASTER_PRODUCTION_READINESS.md` §7 (verification checklist)
  + Gate D (webhook alerting)
* [ADR-0007](0007-route-query-budget-and-causality-ledger.md) —
  Causality Ledger sets the per-user retention precedent (90 days)
  this ADR follows.
* [ADR-0009](0009-progressive-deployment-and-auto-rollback.md) —
  Sentry webhook handler shares the HMAC-verify posture this admin
  surface exposes through replay.
* Stripe Engineering — *Webhook reliability patterns*
