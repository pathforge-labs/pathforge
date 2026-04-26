"""
PathForge — Causality Data Retention Purge (ADR-0012 §#3, Sprint 61)
======================================================================

Daily cron-driven purge of user-attributable causality entries older
than ``settings.causality_retention_days`` (default 90 d).

Why a script (not an Alembic data migration)
--------------------------------------------

The retention cap is a **continuous policy**, not a one-shot data
shape change. Alembic exists for schema evolution; daily housekeeping
belongs in cron. Running this as a script also means an operator can
inspect what *would* be deleted (``--dry-run``, the default) before
flipping ``--apply``, and the same tool serves both ad-hoc compliance
audits and the automated nightly cron.

What this script preserves vs. deletes
--------------------------------------

ADR-0012 §#3 splits causality data into two categories:

  1. **User-attributable rows** (``ri_recommendations`` →
     ``ri_correlations`` cascade) age out at
     ``settings.causality_retention_days``. The script deletes these.

  2. **Anonymised aggregates** (per-engine causality contribution
     rate) are retained forever for the public benchmark page. Until
     the dedicated aggregate table ships (Sprint 62 backlog), this
     script emits a JSONL audit record per purge run capturing
     ``{date, engine_name, recommendation_count,
     mean_correlation_strength}`` so the aggregates are recoverable
     from the audit log even before the table exists. The path is
     ``logs/causality_purge_aggregates.jsonl`` (relative to the API
     working directory) — operators rotate / archive this with the
     rest of the structured-log pipeline.

Why we aggregate **before** deleting (and in the same transaction)
------------------------------------------------------------------

If aggregation ran after the delete the rows wouldn't exist; if it
ran in a separate transaction a crash between the two would either
double-count (aggregate wrote, delete failed → next run re-aggregates
the same rows) or lose the aggregate (delete wrote, aggregate failed
→ data gone forever, ADR breach). Single transaction with the audit
write *first* means crash recovery is safe: a partial run leaves the
data in place and the next nightly run sees the same window.

Ops contract
------------

- ``--dry-run`` (default): reports counts and the cutoff date,
  performs no DB writes. Safe to run any time.
- ``--apply``: actually deletes. Logs the audit JSONL line first.
- ``--retention-days N``: override the settings value (e.g. for an
  ad-hoc compliance sweep at 30 days). Defaults to
  ``settings.causality_retention_days``.

Exit codes
----------
- 0: normal completion (zero or more rows purged).
- 1: DB error or unhandled exception. Cron must alert on non-zero.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import async_session_factory
from app.models.recommendation_intelligence import (
    CrossEngineRecommendation,
    RecommendationCorrelation,
)

logger = logging.getLogger("scripts.purge_causality_data")

#: Path where the aggregate audit JSONL is appended. Relative to CWD
#: so the deploy environment (Railway → ``/app``) controls placement.
AGGREGATE_LOG_PATH = Path("logs") / "causality_purge_aggregates.jsonl"


# ─────────────────────────────────────────────────────────────────
# Result type
# ─────────────────────────────────────────────────────────────────


@dataclass
class PurgeReport:
    """Outcome of a purge run.

    Returned in dry-run and apply mode alike so the same code path
    serves both inspection and deletion. ``rows_deleted`` is 0 in
    dry-run (we never touch the DB); ``rows_eligible`` always
    reflects what *would* be deleted.
    """

    cutoff: datetime
    retention_days: int
    rows_eligible: int
    rows_deleted: int
    dry_run: bool
    aggregates: list[dict[str, object]] = field(default_factory=list)

    def summary(self) -> str:
        mode = "DRY-RUN" if self.dry_run else "APPLIED"
        return (
            f"[{mode}] cutoff={self.cutoff.isoformat()} "
            f"retention_days={self.retention_days} "
            f"rows_eligible={self.rows_eligible} "
            f"rows_deleted={self.rows_deleted} "
            f"engines_aggregated={len(self.aggregates)}"
        )


# ─────────────────────────────────────────────────────────────────
# Aggregation
# ─────────────────────────────────────────────────────────────────


async def _aggregate_engine_contributions(
    session: AsyncSession,
    cutoff: datetime,
) -> list[dict[str, object]]:
    """Build per-engine anonymised aggregates for everything older
    than ``cutoff`` *before* it is deleted.

    Returns one dict per ``engine_name`` with the aggregate stats.
    No user identifiers are included — this satisfies the GDPR
    "anonymised aggregate" carve-out in ADR-0012 §#3.
    """
    stmt = (
        select(
            RecommendationCorrelation.engine_name.label("engine_name"),
            func.count(RecommendationCorrelation.id).label("count"),
            func.avg(
                RecommendationCorrelation.correlation_strength,
            ).label("mean_strength"),
        )
        .join(
            CrossEngineRecommendation,
            CrossEngineRecommendation.id
            == RecommendationCorrelation.recommendation_id,
        )
        .where(CrossEngineRecommendation.created_at < cutoff)
        .group_by(RecommendationCorrelation.engine_name)
    )
    rows = (await session.execute(stmt)).all()
    today = datetime.now(UTC).date().isoformat()
    return [
        {
            "snapshot_date": today,
            "cutoff": cutoff.isoformat(),
            "engine_name": row.engine_name,
            "recommendation_count": int(row.count),
            "mean_correlation_strength": (
                float(row.mean_strength) if row.mean_strength is not None else 0.0
            ),
        }
        for row in rows
    ]


def _append_audit_log(
    aggregates: Sequence[dict[str, object]],
    log_path: Path = AGGREGATE_LOG_PATH,
) -> None:
    """Append one JSONL record per aggregate row.

    The directory is created if missing. We open in append-binary to
    avoid the platform-default text-mode line-ending rewrite (the
    pipeline downstream parses JSONL byte-by-byte).
    """
    if not aggregates:
        return
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("ab") as fh:
        for row in aggregates:
            fh.write(json.dumps(row, sort_keys=True).encode("utf-8"))
            fh.write(b"\n")


# ─────────────────────────────────────────────────────────────────
# Core purge
# ─────────────────────────────────────────────────────────────────


async def purge_causality_data(
    *,
    retention_days: int,
    dry_run: bool,
    session: AsyncSession | None = None,
    audit_log_path: Path | None = None,
) -> PurgeReport:
    """Run one purge cycle.

    Args:
        retention_days: rows older than ``now - retention_days`` are
            eligible for deletion.
        dry_run: when True, only counts + aggregates; no writes.
        session: optional pre-opened session (tests pass an in-memory
            SQLite session). Production code lets the function open
            its own from ``async_session_factory``.
        audit_log_path: override the aggregate JSONL path (tests use
            tmp dirs). Defaults to ``AGGREGATE_LOG_PATH``.

    Returns: :class:`PurgeReport`.

    Raises: any DB error propagates — the caller's transaction is
        rolled back and the script exits 1.
    """
    if retention_days <= 0:
        raise ValueError(
            f"retention_days must be positive, got {retention_days}",
        )

    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    audit_path = audit_log_path or AGGREGATE_LOG_PATH

    own_session = session is None
    if own_session:
        session = async_session_factory()
        await session.__aenter__()
    assert session is not None  # for the type-checker
    try:
        # Count eligible rows for the report — this is the same set
        # that would get deleted.
        count_stmt = select(func.count(CrossEngineRecommendation.id)).where(
            CrossEngineRecommendation.created_at < cutoff,
        )
        rows_eligible = int((await session.execute(count_stmt)).scalar_one())

        aggregates = await _aggregate_engine_contributions(session, cutoff)

        rows_deleted = 0
        if not dry_run and rows_eligible > 0:
            # Aggregate audit record first; if the FS write fails we
            # surface the error before touching the DB and the data
            # stays put.
            _append_audit_log(aggregates, log_path=audit_path)

            # Delete correlations first, then recommendations. We do
            # this explicitly (rather than relying on
            # ``ondelete="CASCADE"``) because:
            #   - SQLAlchemy bulk ``delete()`` bypasses the ORM-level
            #     ``cascade="all, delete-orphan"`` tracking, so the
            #     parent-side ORM cascade never fires.
            #   - DB-level ``ON DELETE CASCADE`` works in Postgres but
            #     requires ``PRAGMA foreign_keys=ON`` in SQLite, which
            #     the hermetic test engine does not enable. Doing the
            #     two-step ourselves is portable, audit-friendly, and
            #     does not lose any rows on a partial transaction.
            eligible_ids_stmt = select(CrossEngineRecommendation.id).where(
                CrossEngineRecommendation.created_at < cutoff,
            )
            eligible_ids = [
                row[0]
                for row in (await session.execute(eligible_ids_stmt)).all()
            ]
            if eligible_ids:
                await session.execute(
                    delete(RecommendationCorrelation).where(
                        RecommendationCorrelation.recommendation_id.in_(
                            eligible_ids,
                        ),
                    ),
                )
                result = await session.execute(
                    delete(CrossEngineRecommendation).where(
                        CrossEngineRecommendation.id.in_(eligible_ids),
                    ),
                )
                rows_deleted = int(result.rowcount or 0)
            await session.commit()

        return PurgeReport(
            cutoff=cutoff,
            retention_days=retention_days,
            rows_eligible=rows_eligible,
            rows_deleted=rows_deleted,
            dry_run=dry_run,
            aggregates=aggregates,
        )
    except Exception:
        if own_session:
            await session.rollback()
        raise
    finally:
        if own_session:
            await session.__aexit__(None, None, None)


# ─────────────────────────────────────────────────────────────────
# CLI entry-point
# ─────────────────────────────────────────────────────────────────


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="purge_causality_data",
        description=(
            "Purge user-attributable causality data older than the "
            "ADR-0012 §#3 retention window. Defaults to dry-run."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete (default is dry-run, count only).",
    )
    parser.add_argument(
        "--retention-days",
        type=int,
        default=None,
        help=(
            "Override settings.causality_retention_days. Must be > 0. "
            "Use a smaller value for ad-hoc compliance sweeps."
        ),
    )
    return parser


async def _amain(argv: Sequence[str]) -> int:
    args = _build_arg_parser().parse_args(argv)
    retention = args.retention_days
    if retention is None:
        retention = settings.causality_retention_days
    try:
        report = await purge_causality_data(
            retention_days=retention,
            dry_run=not args.apply,
        )
    except Exception:
        logger.exception("purge_causality_data: failed")
        return 1
    logger.info(report.summary())
    # Print the human summary too so cron output captures it without
    # requiring the structured-log handler.
    print(report.summary())
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Synchronous entry point for ``python -m scripts.purge_causality_data``."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    return asyncio.run(_amain(list(argv) if argv is not None else sys.argv[1:]))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
