# Sprint 34 — Monetization & Growth Architecture

> **Sprint**: 34 | **Date**: 2026-03-02 | **Audit**: 3 passes, 36 findings

## Principles

1. **Decoupled Gating** — FastAPI dependency, not embedded in engines
2. **Webhook-Driven State** — Stripe is source of truth; backend reacts idempotently
3. **Idempotent Processing** — `stripe_event_id` unique prevents duplicates
4. **State Machine** — Explicit valid status transitions with row-level locking (F25)
5. **Fast Webhook Ack** — Validate + persist → 200; process async (F16)
6. **Raw Body** — `Request.body()` before parsing for Stripe signature (F35)
7. **Privacy-First** — Unpublished by default, noindex headers (F6)
8. **Pattern Conformance** — StrEnum, CheckConstraint, stdlib logging, ConfigDict, OpenAPI tags

## Data Model

```
users (+role column, +subscription relationship)
  ├── subscriptions (1:1, CASCADE) ─ tier, status, Stripe IDs, last_event_timestamp
  │     └── usage_records (1:N) ─ per-period scan counts, compound index
  ├── billing_events (1:N) ─ idempotent event log, trimmed payloads
  ├── admin_audit_logs (1:N) ─ admin action trail
  ├── waitlist_entries (0:1) ─ email normalized, FIFO position
  └── public_career_profiles (0:1) ─ opt-in, slug with reserved words check
```

## Pricing

| Tier    | Monthly | Annual | Engines | Scans/mo |
| :------ | :------ | :----- | :------ | :------- |
| Free    | €0      | —      | 2       | 3        |
| Pro     | €14.99  | €149   | 8       | 30       |
| Premium | €29.99  | €299   | 12      | ∞        |

## API Surface — 27 Endpoints

| Prefix                     | Count | Auth         | Tags            |
| :------------------------- | :---- | :----------- | :-------------- |
| `/api/v1/billing/`         | 7     | User + Admin | Billing         |
| `/api/v1/webhooks/stripe`  | 1     | Signature    | Billing         |
| `/api/v1/admin/`           | 8     | Admin RBAC   | Admin Dashboard |
| `/api/v1/waitlist/`        | 5     | Mixed        | Waitlist        |
| `/api/v1/public-profiles/` | 6     | Mixed        | Public Profiles |

## Audit Summary — 36 Findings

| Pass | Focus                | Findings |
| :--- | :------------------- | :------- |
| 1    | Architecture & logic | F1–F12   |
| 2    | Pattern conformance  | F13–F24  |
| 3    | Production hardening | F25–F36  |

## Dependencies

- `stripe>=14.0.0` (NEW)
- All other: existing stack
