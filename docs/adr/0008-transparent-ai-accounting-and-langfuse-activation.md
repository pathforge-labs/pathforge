# ADR-0008 — Transparent AI Accounting + Langfuse Activation

* **Status:** Accepted
* **Sprint:** 56 (T4 of `docs/architecture/sprint-55-58-code-side-readiness.md`)
* **Closes:** N-5 (`docs/MASTER_PRODUCTION_READINESS.md` §3.3)
* **Supersedes:** `docs/PLAN-langfuse-observability.md` (kept as historical
  context; this ADR is now the source of truth)
* **Date:** 2026-04-25
* **Author:** PathForge engineering
* **Reviewers:** belengaz, reso, pizmam

## Context

Two open readiness items converge on the same data:

* **N-5 (operator visibility).** `docs/PLAN-langfuse-observability.md`
  scoped activation but stalled because OPS-3 (Anthropic / Google /
  Voyage API keys) gated *meaningful* traces. Code is wired; activation
  is one Railway env-var set.
* **Sprint plan §1.3 differentiator.** PathForge's business model has
  the user as customer (paying for AI engines). Surfacing AI accounting
  to the user is **alignment with that model** — competitors with
  user-as-product economics never expose cost or scan-count.

T4 ships both layers in one PR because they share a data source: the
`AITransparencyRecord` rows already persisted on every LLM call.

## Decision

### Layer 1 — Operator (Langfuse traces)

Promote the existing `PLAN-langfuse-observability.md` to canonical
guidance.  Activation is the four Railway env vars listed in §3 of the
plan; no application change required (the code is wired).  Default
sampling: 10 %, PII redaction on.  Once activated, every LLM /
embedding call ships a trace with the engine name, model, tier, prompt
+ completion tokens, latency, retry count, and cost.

### Layer 2 — User (Transparent AI Accounting)

A new dashboard page surfaces, per engine, what AI work the user has
consumed in the current month.  The presentation is **tier-aware
client-side** but the API is **dual-display server-side**:

| Tier | Primary signal | Secondary signal |
|:--|:--|:--|
| Free | "X / Y monthly scans used" (count) | EUR cost as fine-print "estimated AI cost: €0.42" |
| Premium | "Estimated EUR cost: €0.42 this month" | Per-engine call counts |

Per the sprint plan §12 default decision **#4 = dual-display**, the
single API response (`GET /api/v1/ai-usage/summary`) carries
**both** fields; the web layer chooses which to surface based on the
caller's subscription tier.  This means a single deploy can flip a
user between free / premium without redeploying the API, and the
"premium opts into EUR" flag from the original spec becomes a UI
preference rather than an API-shape choice.

### Cost computation

Cost is a **derived quantity**, not a stored column.  Every record
carries `model` + `prompt_tokens` + `completion_tokens`; the service
multiplies through a server-side price table at read time.  Why:

1. Provider prices change retroactively (Anthropic, Google, Voyage all
   re-tier periodically).  Re-pricing historical records on
   price-table refresh requires the source of truth to be
   tokens-and-model, not a pre-computed cost column.
2. A column would create a consistency hazard between the column and
   the price table.

Trade-off: one extra multiplication per record at read time —
negligible for the per-user, per-month aggregate workload.

### Unknown-model handling

Records carrying a model name not in the price table contribute to
the call count but **not** the cost total.  The summary response
sets `has_unpriced_models: true` so the UI can warn "cost estimate
excludes some calls" rather than silently under-report.  This is
purposeful — under-reporting cost is a trust violation; missing-data
disclosure is not.

## Considered alternatives

* **Store cost on the record at call time.**  Rejected — see above
  on retroactive re-pricing.
* **Single-presentation API (free OR premium, not both).**  Rejected
  — couples the API surface to the subscription model, complicates
  tier upgrades, and requires a redeploy whenever the tier mapping
  changes.
* **Live FX conversion for USD → EUR.**  Rejected — the same record
  must report the same EUR figure across audits.  We pin
  `EUR_PER_USD = 0.94` and refresh quarterly with the price table.
* **Aggregate via a materialised view.**  Rejected for now — daily
  aggregate volume is well within the 12-engine × monthly grouping
  the on-the-fly query handles.  Revisit if `/ai-usage/summary` p95
  exceeds T3's 25 % threshold.

## Implementation

| Layer | File(s) | Role |
|:---|:---|:---|
| Service | `app/services/ai_usage_service.py` (new) | Aggregates `AITransparencyRecord` rows; in-memory price table; dual-display response. |
| Schema | `app/schemas/ai_usage.py` (new) | `UsageSummaryResponse` + `EngineUsageResponse`. |
| Route | `app/api/v1/ai_usage.py` (new) | `GET /api/v1/ai-usage/summary?period=current_month`; rate-limited 60 / minute; query-budget 4 (per the route's measured pass under the T2-rollout fixture). |
| Operator activation | `docs/PLAN-langfuse-observability.md` (existing) | Canonical instructions for the four Railway env vars. |
| Web (T4 follow-up PR) | `apps/web/src/app/dashboard/settings/ai-usage/page.tsx` | Renders the summary tier-aware. |
| E2E (T4 follow-up PR) | `apps/web/e2e/ai-usage.spec.ts` | dashboard renders, decimals correct, tier-aware messaging, axe-core a11y zero-violations. |

## Privacy & GDPR

* `AITransparencyRecord` rows are per-user and link to `user_id`.
* The `DELETE /api/v1/users/me` endpoint already cascades through
  the table; this PR introduces no new retention policy.
* Langfuse PII redaction stays on by default
  (`langfuse_pii_redaction=True`).  The summary endpoint surfaces
  only counts and aggregated numbers; no raw prompt or completion
  payloads cross the boundary.

## Performance impact

* Summary endpoint: single SELECT against
  `ai_transparency_records`, indexed on `(user_id, analysis_type)` +
  `(created_at)`.  For a heavy-user-month (~ 200 records) the
  aggregation completes in < 30 ms p99 on the dev DB.
* Price table is module-level; no per-call I/O.
* Endpoint declared `@route_query_budget(max_queries=4)` — three
  queries observed in the integration test (auth, summary SELECT,
  rate-limit bookkeeping); 4 leaves the standard 25 % headroom.

## Rollback

Removing the `application.include_router(ai_usage.router, …)` line in
`apps/api/app/main.py` un-mounts the endpoint; the service module and
schema can stay in place harmlessly.  The summary read is read-only —
no DB schema or migration to revert.

## Quality gate

Per `docs/architecture/sprint-55-58-code-side-readiness.md` §5.5 (T4):

| Criterion | Target | Status |
|:---|:---:|:---|
| Langfuse traces shipping | 100 % of LLM calls | ✅ Code wired (existing); activation = 4 env vars (operator action, runbook in PLAN-langfuse-observability.md) |
| `/ai-usage/summary` covered | ≥ 90 % | ✅ This PR ships 14 tests (9 service + 5 route) covering empty, multi-engine aggregation, period filter, unknown-model fallback, tier auth gating, period validation |
| User-facing page accessible | yes | 🚧 Web layer + axe scan land in the T4 follow-up PR |
| User test ≥ 4 / 5 | usability | 🚧 Web layer dependency |

The web layer + E2E land as **PR T4-web** so this PR stays
backend-only and reviewable against the API surface contract.

## References

* `docs/architecture/sprint-55-58-code-side-readiness.md` §5
* `docs/PLAN-langfuse-observability.md` (operator activation runbook,
  unchanged)
* ADR-0007 — query budget + Engine-of-Record Causality.  Engine-name
  derivation matches the `analysis_type` field on every record, so
  the future Causality Ledger can join through the same column.
