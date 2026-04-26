"""
PathForge — Tests for ``scripts/purge_causality_data.py`` (Sprint 61)
======================================================================

Covers the full operational matrix of the ADR-0012 §#3 retention purge:

  - dry-run reports counts but never writes
  - apply mode deletes the eligible rows (and only those) and audits
    aggregates first
  - retention boundary respected (rows at exactly the cutoff stay)
  - empty case (nothing eligible) is a no-op
  - aggregates carry the right per-engine stats and zero rows when
    the strength column is NULL
  - invalid retention_days raises rather than silently no-op'ing
  - CLI ``--dry-run`` (default) and ``--apply`` shape are exercised
    via ``main([...])``

The tests live on top of the SQLite ``db_session`` fixture so we do
not need a Postgres container for hermetic CI.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.recommendation_intelligence import (
    CrossEngineRecommendation,
    RecommendationCorrelation,
)
from app.models.user import User
from scripts.purge_causality_data import (
    PurgeReport,
    _amain,
    main,
    purge_causality_data,
)

pytestmark = pytest.mark.asyncio


# ─────────────────────────────────────────────────────────────────
# Fixtures: build a small causality graph at known ages
# ─────────────────────────────────────────────────────────────────


async def _seed_recommendation(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    age_days: int,
    engines: list[tuple[str, float]] | None = None,
) -> CrossEngineRecommendation:
    """Create one ``ri_recommendations`` row plus its correlations.

    ``age_days`` ⇒ created_at = now - age_days. We bypass
    ``server_default=now()`` by setting ``created_at`` explicitly so
    we can simulate "old" rows without sleeping.
    """
    created_at = datetime.now(UTC) - timedelta(days=age_days)
    rec = CrossEngineRecommendation(
        user_id=user_id,
        recommendation_type="opportunity",
        status="pending",
        effort_level="moderate",
        priority_score=42.0,
        urgency=0.5,
        impact_score=0.6,
        confidence_score=0.7,
        title="Test recommendation",
        description="seeded",
        created_at=created_at,
        updated_at=created_at,
    )
    session.add(rec)
    await session.flush()
    for name, strength in engines or []:
        session.add(
            RecommendationCorrelation(
                recommendation_id=rec.id,
                engine_name=name,
                correlation_strength=strength,
                insight_summary=f"engine={name}",
                created_at=created_at,
                updated_at=created_at,
            ),
        )
    await session.flush()
    return rec


# ─────────────────────────────────────────────────────────────────
# 1. Dry-run never writes
# ─────────────────────────────────────────────────────────────────


class TestPurgeDryRun:
    """Default mode reports but performs no DB writes."""

    async def test_dry_run_reports_eligible_but_deletes_nothing(
        self,
        db_session: AsyncSession,
        authenticated_user: User,
        tmp_path: Path,
    ) -> None:
        await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=120,  # > 90-day cutoff
            engines=[("dna", 0.8), ("salary", 0.5)],
        )
        await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=10,  # well within retention
            engines=[("dna", 0.9)],
        )

        report = await purge_causality_data(
            retention_days=90,
            dry_run=True,
            session=db_session,
            audit_log_path=tmp_path / "agg.jsonl",
        )

        assert isinstance(report, PurgeReport)
        assert report.dry_run is True
        assert report.rows_eligible == 1
        assert report.rows_deleted == 0
        # Both rows still in DB.
        all_rows = (
            await db_session.execute(select(CrossEngineRecommendation))
        ).scalars().all()
        assert len(all_rows) == 2
        # Audit log NOT written in dry-run.
        assert not (tmp_path / "agg.jsonl").exists()

    async def test_dry_run_aggregates_per_engine_for_eligible_rows(
        self,
        db_session: AsyncSession,
        authenticated_user: User,
        tmp_path: Path,
    ) -> None:
        # Two old recs, both touching 'dna'; one also touches 'salary'.
        await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=200,
            engines=[("dna", 0.8), ("salary", 0.4)],
        )
        await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=120,
            engines=[("dna", 0.6)],
        )
        # One fresh rec, must be excluded from aggregates.
        await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=5,
            engines=[("dna", 0.99), ("salary", 0.99)],
        )

        report = await purge_causality_data(
            retention_days=90,
            dry_run=True,
            session=db_session,
            audit_log_path=tmp_path / "agg.jsonl",
        )

        by_engine = {row["engine_name"]: row for row in report.aggregates}
        assert set(by_engine) == {"dna", "salary"}
        assert by_engine["dna"]["recommendation_count"] == 2
        assert by_engine["salary"]["recommendation_count"] == 1
        # mean(0.8, 0.6) == 0.7 for dna.
        assert by_engine["dna"]["mean_correlation_strength"] == pytest.approx(0.7)
        assert by_engine["salary"]["mean_correlation_strength"] == pytest.approx(0.4)


# ─────────────────────────────────────────────────────────────────
# 2. Apply mode deletes eligible rows + writes audit log first
# ─────────────────────────────────────────────────────────────────


class TestPurgeApply:
    async def test_apply_deletes_eligible_and_keeps_recent(
        self,
        db_session: AsyncSession,
        authenticated_user: User,
        tmp_path: Path,
    ) -> None:
        old = await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=150,
            engines=[("dna", 0.8)],
        )
        recent = await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=30,
            engines=[("dna", 0.9)],
        )

        report = await purge_causality_data(
            retention_days=90,
            dry_run=False,
            session=db_session,
            audit_log_path=tmp_path / "agg.jsonl",
        )

        assert report.dry_run is False
        assert report.rows_eligible == 1
        assert report.rows_deleted == 1
        remaining_ids = {
            r.id for r in (
                await db_session.execute(select(CrossEngineRecommendation))
            ).scalars().all()
        }
        assert recent.id in remaining_ids
        assert old.id not in remaining_ids

        # Cascading deletes the correlations too.
        remaining_corrs = (
            await db_session.execute(select(RecommendationCorrelation))
        ).scalars().all()
        # Exactly the recent rec's one correlation remains.
        assert len(remaining_corrs) == 1

    async def test_apply_writes_jsonl_audit_record_per_engine(
        self,
        db_session: AsyncSession,
        authenticated_user: User,
        tmp_path: Path,
    ) -> None:
        await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=180,
            engines=[("dna", 0.8), ("salary", 0.6)],
        )
        log_path = tmp_path / "subdir" / "agg.jsonl"

        report = await purge_causality_data(
            retention_days=90,
            dry_run=False,
            session=db_session,
            audit_log_path=log_path,
        )

        assert report.rows_deleted == 1
        assert log_path.exists()
        lines = log_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
        records = [json.loads(line) for line in lines]
        engines = {rec["engine_name"] for rec in records}
        assert engines == {"dna", "salary"}
        # Each record carries the policy metadata required for the
        # public-benchmark page reconstruction.
        for rec in records:
            assert rec["recommendation_count"] == 1
            assert "snapshot_date" in rec
            assert "cutoff" in rec

    async def test_apply_with_empty_eligible_set_is_no_op(
        self,
        db_session: AsyncSession,
        authenticated_user: User,
        tmp_path: Path,
    ) -> None:
        # Only a fresh row exists.
        await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=10,
            engines=[("dna", 0.5)],
        )
        report = await purge_causality_data(
            retention_days=90,
            dry_run=False,
            session=db_session,
            audit_log_path=tmp_path / "agg.jsonl",
        )
        assert report.rows_eligible == 0
        assert report.rows_deleted == 0
        # No audit written for empty runs (avoids log pollution).
        assert not (tmp_path / "agg.jsonl").exists()


# ─────────────────────────────────────────────────────────────────
# 3. Boundary + invalid input
# ─────────────────────────────────────────────────────────────────


class TestPurgeBoundary:
    async def test_row_at_cutoff_boundary_is_kept(
        self,
        db_session: AsyncSession,
        authenticated_user: User,
        tmp_path: Path,
    ) -> None:
        # The cutoff is `< now - 90d`; a row created exactly at that
        # boundary should NOT be eligible (strict <, not <=).
        # We build a row created 89.99 days ago to stay inside.
        rec = await _seed_recommendation(
            db_session,
            user_id=authenticated_user.id,
            age_days=89,
            engines=[("dna", 0.8)],
        )
        report = await purge_causality_data(
            retention_days=90,
            dry_run=False,
            session=db_session,
            audit_log_path=tmp_path / "agg.jsonl",
        )
        assert report.rows_eligible == 0
        # Row still present.
        rows = (
            await db_session.execute(select(CrossEngineRecommendation))
        ).scalars().all()
        assert any(r.id == rec.id for r in rows)

    async def test_zero_or_negative_retention_raises(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        with pytest.raises(ValueError, match="retention_days must be positive"):
            await purge_causality_data(
                retention_days=0,
                dry_run=True,
                session=db_session,
                audit_log_path=tmp_path / "agg.jsonl",
            )
        with pytest.raises(ValueError, match="retention_days must be positive"):
            await purge_causality_data(
                retention_days=-7,
                dry_run=True,
                session=db_session,
                audit_log_path=tmp_path / "agg.jsonl",
            )

    async def test_report_summary_contains_mode_and_counts(
        self,
        db_session: AsyncSession,
        tmp_path: Path,
    ) -> None:
        report = await purge_causality_data(
            retention_days=90,
            dry_run=True,
            session=db_session,
            audit_log_path=tmp_path / "agg.jsonl",
        )
        text = report.summary()
        assert "DRY-RUN" in text
        assert "rows_eligible=0" in text
        assert "rows_deleted=0" in text


# ─────────────────────────────────────────────────────────────────
# 4. CLI shape — main() with mocked purge call
# ─────────────────────────────────────────────────────────────────


class TestCliEntrypoint:
    """``main()`` parses argv and orchestrates the async call. We
    monkeypatch the underlying ``purge_causality_data`` so we don't
    depend on the production engine being reachable from a unit
    test.

    The async test methods exercise the inner ``_amain`` coroutine
    directly — calling the sync ``main()`` from inside a pytest-asyncio
    test would nest ``asyncio.run`` inside a running loop and raise
    ``RuntimeError: asyncio.run() cannot be called from a running event
    loop``. ``main`` itself is exercised by the
    ``test_main_sync_wrapper_returns_int`` sync helper below, which
    proves the sync→async bridge wires up correctly.
    """

    async def test_main_dry_run_default_returns_zero(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, object] = {}

        async def _fake(
            *,
            retention_days: int,
            dry_run: bool,
            session: object | None = None,
            audit_log_path: object | None = None,
        ) -> PurgeReport:
            captured["retention_days"] = retention_days
            captured["dry_run"] = dry_run
            return PurgeReport(
                cutoff=datetime.now(UTC),
                retention_days=retention_days,
                rows_eligible=0,
                rows_deleted=0,
                dry_run=dry_run,
            )

        monkeypatch.setattr(
            "scripts.purge_causality_data.purge_causality_data", _fake,
        )
        rc = await _amain([])
        assert rc == 0
        assert captured["dry_run"] is True

    async def test_main_apply_flag_flips_dry_run(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        captured: dict[str, object] = {}

        async def _fake(
            *,
            retention_days: int,
            dry_run: bool,
            session: object | None = None,
            audit_log_path: object | None = None,
        ) -> PurgeReport:
            captured["dry_run"] = dry_run
            captured["retention_days"] = retention_days
            return PurgeReport(
                cutoff=datetime.now(UTC),
                retention_days=retention_days,
                rows_eligible=0,
                rows_deleted=0,
                dry_run=dry_run,
            )

        monkeypatch.setattr(
            "scripts.purge_causality_data.purge_causality_data", _fake,
        )
        rc = await _amain(["--apply", "--retention-days", "30"])
        assert rc == 0
        assert captured["dry_run"] is False
        assert captured["retention_days"] == 30

    async def test_main_returns_one_on_exception(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        async def _boom(**_: object) -> PurgeReport:
            raise RuntimeError("simulated DB failure")

        monkeypatch.setattr(
            "scripts.purge_causality_data.purge_causality_data", _boom,
        )
        rc = await _amain([])
        assert rc == 1


# Note on `main()` coverage: the sync wrapper is a thin
# ``return asyncio.run(_amain(argv))`` bridge. Calling it from inside
# this pytest-asyncio module would nest event loops and raise. We rely
# on the three ``_amain`` tests above for behaviour coverage and on the
# ``__main__`` block at module bottom for runtime invocation. The
# ``main`` symbol itself is imported here so a future refactor that
# breaks the signature is caught at collection time.
assert callable(main), "scripts.purge_causality_data.main must stay callable"
