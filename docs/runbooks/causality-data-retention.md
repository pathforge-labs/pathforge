# Causality Data Retention Runbook

> **Sprint 61 / [ADR-0012 §#3](../adr/0012-sprint-55-58-decisions-resolved.md#3--causality-data-retention-90-day-rolling).**
> Operational guide for the daily purge of user-attributable causality
> data (`ri_recommendations` + `ri_correlations`) and the anonymised
> aggregate audit log.

---

## TL;DR

| Symptom | First action |
|:---|:---|
| Cron alert: `purge_causality_data` exited non-zero | **§ 1 — Triage a failed purge** |
| GDPR DSR (data-subject request) demands earlier purge | **§ 2 — Ad-hoc compliance sweep** |
| Public-benchmark page needs historical aggregates | **§ 3 — Read the audit log** |
| Need to confirm the daily cron is running | **§ 4 — Verify cron health** |

---

## Background

ADR-0012 §#3 sets a **90-day rolling window** on user-attributable
causality data. Per-user rows age out; **anonymised per-engine
aggregates are retained forever** for the public benchmark page. The
script `apps/api/scripts/purge_causality_data.py`:

1. Counts eligible rows (`ri_recommendations.created_at < now − 90d`).
2. Builds per-engine aggregates (`engine_name`, `count`,
   `mean_correlation_strength`).
3. Appends one JSONL record per engine to
   `logs/causality_purge_aggregates.jsonl` **before** issuing the
   delete (crash-safe ordering — see ADR-0012).
4. Deletes correlations first, then recommendations, in a single
   transaction.

The script is **dry-run by default**. Cron uses `--apply`.

---

## 1. Triage a failed purge

```bash
# 1. Dry-run from a bastion/Railway shell — never deletes.
python -m scripts.purge_causality_data
#   [DRY-RUN] cutoff=2026-01-27T... retention_days=90 \
#     rows_eligible=N rows_deleted=0 engines_aggregated=K

# 2. If N == 0 the cron just had nothing to do — close the alert.

# 3. If the dry-run errored too, check the standard suspects:
#    - DATABASE_URL reachable?       psql "$DATABASE_URL" -c '\dt'
#    - logs/ directory writable?     touch logs/.write-test
#    - migrations applied?           alembic current

# 4. If the error is transient (DB blip), let the next nightly cron retry.
#    The aggregate log is append-only and the purge transaction is atomic
#    — a half-finished run cannot leave the DB in a bad state.
```

If the failure persists for **two consecutive nights**, page the data
team — we are accumulating GDPR-overdue rows.

## 2. Ad-hoc compliance sweep

For an in-window DSR (the user's data must be deleted faster than
90 d):

```bash
# Drop a row count first to size the sweep.
python -m scripts.purge_causality_data --retention-days 7

# Apply with the same window.
python -m scripts.purge_causality_data --retention-days 7 --apply
```

Targeted single-user deletion (when only one user must be erased)
should go through the user-deletion endpoint instead — it cascades
through every PII-bearing table, not just causality data. Use this
script only when the policy applies to **all** users beyond a tighter
window.

## 3. Read the audit log

```bash
# All aggregates from the last week, pretty-printed.
tail -n 1000 logs/causality_purge_aggregates.jsonl | \
  jq 'select(.snapshot_date >= "2026-04-20")'

# Per-engine recommendation count for a given month.
jq -r 'select(.snapshot_date | startswith("2026-04")) |
       [.snapshot_date, .engine_name, .recommendation_count] | @tsv' \
  logs/causality_purge_aggregates.jsonl
```

The JSONL fields:

| Field | Meaning |
|:---|:---|
| `snapshot_date` | UTC date the purge ran |
| `cutoff` | ISO timestamp of the retention cutoff |
| `engine_name` | `dna`, `salary`, `passport`, … |
| `recommendation_count` | rows being purged that touched this engine |
| `mean_correlation_strength` | average `correlation_strength` (0–1) |

The aggregates are intentionally **per-engine, per-day** — they
support the "engine X contributed to Y % of recommendations across
all time" headline number on the public-benchmark page without ever
attributing any single row to a user.

## 4. Verify cron health

The recommended cron entry (Railway "scheduled task" pane):

```cron
# Daily 02:15 UTC — quiet window between EU evening and US wake-up.
15 2 * * * cd /app && python -m scripts.purge_causality_data --apply
```

Last-run check (assumes the structured-log handler tags it):

```bash
# In Railway logs, last 7 days:
railway logs --since 7d 2>&1 | grep 'scripts.purge_causality_data'
```

Expected: **one** `[APPLIED] cutoff=… rows_eligible=N rows_deleted=N`
line per night. Anything else (zero lines, multiple lines per night,
non-zero exit) is a paging event.

---

## Rollback

The script writes the aggregate audit log **before** the delete, in
the same transaction. If you need to undo a purge:

- The deleted user-attributable rows are **gone** (this is the
  point of the script — that's the GDPR contract).
- The aggregates remain in `logs/causality_purge_aggregates.jsonl`
  and the public benchmark page can still use them.

The script has no "un-purge" mode by design. If a deletion was
issued in error (e.g. `--retention-days 1` typo), the only recovery
path is the **PostgreSQL PITR restore** documented in
[`production-checklist.md`](./production-checklist.md). Filing a
PITR ticket should be the *first* response to a wrong-window
incident — every minute of WAL replay shrinks the recovery window.

---

## Tests

```bash
cd apps/api
pytest tests/test_scripts_purge_causality_data.py -v
```

The hermetic test fixture seeds rows at known ages (10, 30, 89, 120,
150, 180, 200 days) and asserts dry-run never writes, apply deletes
exactly the eligible set, the cutoff is strict (`<`, not `<=`), and
the audit log carries one record per engine. Run before any change
to the script.
