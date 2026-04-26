# Performance Baselines & Regression Gate

> **T3 / Sprint 56 — closes N-6 in
> [`docs/MASTER_PRODUCTION_READINESS.md`](../MASTER_PRODUCTION_READINESS.md).**
> Tooling that pins per-endpoint p50/p95 latencies for the 17
> baseline-tracked routes, plus a CI gate that fails any PR whose p95
> regresses by > 25 % on any tracked endpoint.

---

## Why this exists

`scripts/perf-baseline.sh` has captured ad-hoc latencies for a year,
but no baseline was committed. "Slowdown" was therefore subjective —
a regressed endpoint became its own baseline. T3 fixes this:

* **Pinned baseline** — `2026-Q2.json` (current). Refreshed quarterly
  *or* whenever a sprint touches a baseline-tracked endpoint
  (whichever comes first). Older baselines stay in this directory as
  historical record (they are not deleted; the gate only consults
  the active one).
* **CI gate** — `.github/workflows/ci.yml` runs the script in
  `--compare-to=…` mode on every PR that touches `apps/api/`. The
  gate is **advisory** when the baseline is the placeholder
  (zero-valued), and **blocking** once a real staging capture has
  populated it.
* **Threshold** — 25 % over baseline p95. Per ADR-0007 §4.2 this is
  intentionally permissive: a *drift detector*, not a fitness gate.
  Endpoint-specific tighter budgets follow Track 2 (query budget,
  ADR-0007) and Track 4 (LLM cost budget, T4).

---

## Active baseline

| File | Window | Status |
|:---|:---|:---|
| **`2026-Q2.json`** | Sprint 55 → 58 | Placeholder pending N-4 staging activation. Refresh after the first successful `deploy-staging.yml` run. |

When a new quarter opens, copy the previous baseline and re-capture
against staging:

```bash
cp docs/baselines/2026-Q2.json docs/baselines/2026-Q3.json
AUTH_TOKEN=$(...)  ./scripts/perf-baseline.sh \
  API_BASE_URL=https://api-staging.pathforge.eu \
  --out=docs/baselines/2026-Q3.json \
  --api-only
```

Then update the **active baseline pointer** in
`.github/workflows/ci.yml` (`PERF_BASELINE_PATH` env var).

---

## Capturing a fresh baseline

### Local capture (development)
```bash
# 1. Start API + DB locally (uvicorn, supabase local stack, …)
# 2. Login as a fixture user and grab a JWT
AUTH_TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"dev@example.com","password":"…"}' | jq -r .access_token)

# 3. Capture
./scripts/perf-baseline.sh \
  --api-only \
  --out=docs/baselines/local-$(date +%Y%m%d).json
```

### Staging capture (canonical baseline source)
Same as local, but:
* `API_BASE_URL=https://api-staging.pathforge.eu`
* Login as the synthetic baseline-fixture user (provisioned in T6
  smoke fixture, `is_synthetic=true`).
* Run from the `update-baselines.yml` workflow so the run is
  reproducible and the artifact is uploaded.

---

## Comparing current vs baseline (regression gate)

```bash
AUTH_TOKEN=$(...)  ./scripts/perf-baseline.sh \
  --compare-to=docs/baselines/2026-Q2.json \
  --threshold=25
```

Exit code:
* `0` — every endpoint within `THRESHOLD %` of baseline p95.
* `1` — at least one endpoint regressed beyond the threshold.
* `2` — invocation error (missing baseline file, no `jq`, etc.).

Output marks each regressed endpoint with `🚨 REGRESSION` and prints a
summary line like `Regressions : 3` so a tail-grep is sufficient for
ad-hoc inspection.

---

## Refresh policy

| Trigger | Action |
|:---|:---|
| **Sprint touches a baseline-tracked endpoint** | Re-capture in the same PR; update the active JSON file. |
| **4 sprints since last refresh** | Re-capture as cron job (`update-baselines.yml`). |
| **Quarter rollover** | Open a new `<YYYY>-Q<N>.json` and update the CI pointer. |
| **CI regression triggered, root cause is a legit improvement on a different endpoint** | Refresh the baseline for that endpoint only via `jq` patch; do **not** wholesale-replace. |

Rationale: the gate's job is to surface unintentional drift. Frequent
refreshes prevent the baseline from becoming stale-against-real-prod
(false positives); rare refreshes prevent legitimate-improvement
ratchets from washing out genuine regressions (false negatives).

---

## File format

```jsonc
{
  "captured_at": "20260425_140000",          // YYYYMMDD_HHMMSS UTC
  "iterations": 20,                          // sample size per endpoint
  "api_base_url": "https://api-staging…",
  "endpoints": [
    {
      "label": "Career DNA",                 // human-readable
      "endpoint": "/api/v1/career-dna",      // path matched by --compare-to
      "p50_ms": 142,
      "p95_ms": 287,
      "iterations": 20
    }
    // … one entry per endpoint
  ]
}
```

The script compares **only on `endpoint`**. Adding a new endpoint to
the baseline doesn't break the gate (the new endpoint has nothing to
compare against — reported as "baseline absent"); removing one is a
silent skip. To enforce coverage on a new endpoint, also list it in
`scripts/perf-baseline.sh`'s `measure …` block.

---

## Related ADRs / docs

* [ADR-0007](../adr/0007-route-query-budget-and-causality-ledger.md)
  — query budget + Engine-of-Record Causality (T2). Per-endpoint
  query bounds complement the latency baseline.
* `docs/architecture/sprint-55-58-code-side-readiness.md` §4 — the
  T3 spec this document implements.
* `docs/MASTER_PRODUCTION_READINESS.md` §3.3 N-6 — the readiness
  finding T3 closes.
