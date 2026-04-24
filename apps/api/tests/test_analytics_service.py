"""
PathForge API — Analytics Service Unit Tests
=============================================
Direct coverage of app.services.analytics_service targeting the
funnel aggregation, market intelligence computations, and CV A/B
experiment helpers without hitting the HTTP layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from app.core.security import hash_password
from app.models.analytics import (
    CVExperiment,
    ExperimentStatus,
    FunnelEvent,
    FunnelStage,
    InsightType,
    MarketInsight,
)
from app.models.application import Application, CVVersion
from app.models.matching import JobListing, MatchResult
from app.models.resume import Resume
from app.models.user import User
from app.services import analytics_service

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


# ─────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────


async def _make_user(db: AsyncSession, email: str = "svc@test.dev") -> User:
    user = User(
        email=email,
        hashed_password=hash_password("Password123!"),
        full_name="Service Tester",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _make_job(
    db: AsyncSession,
    *,
    title: str = "Senior Python Engineer",
    description: str = "We need Python, FastAPI, Postgres skills.",
    created_at: datetime | None = None,
) -> JobListing:
    job = JobListing(
        title=title,
        company="Acme",
        description=description,
    )
    db.add(job)
    await db.flush()
    if created_at is not None:
        job.created_at = created_at
        await db.flush()
    await db.refresh(job)
    return job


async def _make_match(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    score: float = 0.9,
    created_at: datetime | None = None,
) -> MatchResult:
    match = MatchResult(
        user_id=user_id,
        job_listing_id=job_id,
        overall_score=score,
    )
    db.add(match)
    await db.flush()
    if created_at is not None:
        match.created_at = created_at
        await db.flush()
    await db.refresh(match)
    return match


async def _make_application(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
    job_id: uuid.UUID,
    created_at: datetime | None = None,
) -> Application:
    app = Application(
        user_id=user_id,
        job_listing_id=job_id,
        status="saved",
    )
    db.add(app)
    await db.flush()
    if created_at is not None:
        app.created_at = created_at
        await db.flush()
    await db.refresh(app)
    return app


async def _make_resume(db: AsyncSession, *, user_id: uuid.UUID) -> Resume:
    resume = Resume(user_id=user_id, title="Main")
    db.add(resume)
    await db.flush()
    await db.refresh(resume)
    return resume


async def _make_cv_version(
    db: AsyncSession, *, resume_id: uuid.UUID, job_id: uuid.UUID,
) -> CVVersion:
    cv = CVVersion(resume_id=resume_id, job_listing_id=job_id)
    db.add(cv)
    await db.flush()
    await db.refresh(cv)
    return cv


# ─────────────────────────────────────────────────────────────────────────
# _parse_period
# ─────────────────────────────────────────────────────────────────────────


def test_parse_period_valid_30d() -> None:
    assert analytics_service._parse_period("30d") == 30


def test_parse_period_valid_7d() -> None:
    assert analytics_service._parse_period("7d") == 7


def test_parse_period_strips_and_lowercases() -> None:
    assert analytics_service._parse_period("  90D  ") == 90


def test_parse_period_invalid_suffix_returns_default() -> None:
    assert analytics_service._parse_period("30h") == 30


def test_parse_period_invalid_number_returns_default() -> None:
    # endswith 'd' but prefix not numeric → hits except branch (line 292) → default
    assert analytics_service._parse_period("abcd") == 30


def test_parse_period_empty_returns_default() -> None:
    assert analytics_service._parse_period("") == 30


# ─────────────────────────────────────────────────────────────────────────
# record_funnel_event
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_record_funnel_event_persists(db_session: AsyncSession) -> None:
    user = await _make_user(db_session)

    event = await analytics_service.record_funnel_event(
        db_session,
        user_id=user.id,
        application_id=None,
        stage=FunnelStage.VIEWED,
        metadata={"source": "test"},
    )

    assert isinstance(event, FunnelEvent)
    assert event.id is not None
    assert event.user_id == user.id
    assert event.stage == FunnelStage.VIEWED
    assert event.metadata_ == {"source": "test"}


@pytest.mark.asyncio
async def test_record_funnel_event_no_metadata(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="noemail@test.dev")
    event = await analytics_service.record_funnel_event(
        db_session,
        user_id=user.id,
        application_id=None,
        stage=FunnelStage.APPLIED,
    )
    assert event.metadata_ is None
    assert event.stage == FunnelStage.APPLIED


# ─────────────────────────────────────────────────────────────────────────
# get_funnel_metrics
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_funnel_metrics_aggregates_counts(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="metrics@test.dev")
    for stage in [FunnelStage.VIEWED, FunnelStage.VIEWED, FunnelStage.SAVED]:
        await analytics_service.record_funnel_event(
            db_session, user_id=user.id, application_id=None, stage=stage,
        )

    metrics = await analytics_service.get_funnel_metrics(
        db_session, user_id=user.id, period="30d",
    )

    assert metrics["user_id"] == user.id
    assert metrics["period"] == "30d"
    assert metrics["total_events"] == 3
    stages = {s["stage"]: s for s in metrics["stages"]}
    assert stages[FunnelStage.VIEWED]["count"] == 2
    assert stages[FunnelStage.SAVED]["count"] == 1
    assert stages[FunnelStage.VIEWED]["conversion_rate"] == 100.0
    # Saved: 1/2 = 50%
    assert stages[FunnelStage.SAVED]["conversion_rate"] == 50.0
    # Absent stages should be zero
    assert stages[FunnelStage.OFFERED]["count"] == 0
    assert stages[FunnelStage.OFFERED]["conversion_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_funnel_metrics_empty_user(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="emptyfunnel@test.dev")
    metrics = await analytics_service.get_funnel_metrics(
        db_session, user_id=user.id,
    )
    assert metrics["total_events"] == 0
    for s in metrics["stages"]:
        assert s["count"] == 0
        assert s["conversion_rate"] == 0.0


@pytest.mark.asyncio
async def test_get_funnel_metrics_no_viewed_uses_total(
    db_session: AsyncSession,
) -> None:
    """When no VIEWED events exist, top_count falls back to total."""
    user = await _make_user(db_session, email="noview@test.dev")
    await analytics_service.record_funnel_event(
        db_session, user_id=user.id, application_id=None,
        stage=FunnelStage.APPLIED,
    )
    metrics = await analytics_service.get_funnel_metrics(
        db_session, user_id=user.id,
    )
    assert metrics["total_events"] == 1
    stages = {s["stage"]: s for s in metrics["stages"]}
    assert stages[FunnelStage.APPLIED]["count"] == 1
    # 1/1 = 100%
    assert stages[FunnelStage.APPLIED]["conversion_rate"] == 100.0


# ─────────────────────────────────────────────────────────────────────────
# get_funnel_timeline
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_funnel_timeline_groups_by_day(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="timeline@test.dev")
    for _ in range(3):
        await analytics_service.record_funnel_event(
            db_session, user_id=user.id, application_id=None,
            stage=FunnelStage.VIEWED,
        )

    timeline = await analytics_service.get_funnel_timeline(
        db_session, user_id=user.id, days=14,
    )

    assert timeline["user_id"] == user.id
    assert timeline["days"] == 14
    assert isinstance(timeline["data"], list)
    assert len(timeline["data"]) >= 1
    # Each entry has the expected shape
    entry = timeline["data"][0]
    assert set(entry.keys()) == {"date", "stage", "count"}


@pytest.mark.asyncio
async def test_get_funnel_timeline_empty(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="emptytl@test.dev")
    timeline = await analytics_service.get_funnel_timeline(
        db_session, user_id=user.id,
    )
    assert timeline["data"] == []
    assert timeline["days"] == 30


# ─────────────────────────────────────────────────────────────────────────
# generate_market_insight
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generate_market_insight_skill_demand(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="skill@test.dev")
    job = await _make_job(
        db_session,
        description="We use Python, TypeScript, React, Docker, and Kubernetes.",
    )
    await _make_match(db_session, user_id=user.id, job_id=job.id)

    insight = await analytics_service.generate_market_insight(
        db_session,
        user_id=user.id,
        insight_type=InsightType.SKILL_DEMAND,
        period="30d",
    )

    assert isinstance(insight, MarketInsight)
    assert insight.insight_type == InsightType.SKILL_DEMAND
    assert insight.period == "30d"
    assert "top_skills" in insight.data
    assert insight.data["total_listings_analyzed"] == 1
    skills = {entry["skill"] for entry in insight.data["top_skills"]}
    assert {"python", "react", "docker"}.issubset(skills)


@pytest.mark.asyncio
async def test_generate_market_insight_salary_trend(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="salary@test.dev")
    job = await _make_job(db_session)
    await _make_match(db_session, user_id=user.id, job_id=job.id)

    insight = await analytics_service.generate_market_insight(
        db_session,
        user_id=user.id,
        insight_type=InsightType.SALARY_TREND,
    )
    assert insight.data["matches_analyzed"] == 1
    assert insight.data["trend"] == "stable"


@pytest.mark.asyncio
async def test_generate_market_insight_salary_trend_zero_matches(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="salaryzero@test.dev")
    insight = await analytics_service.generate_market_insight(
        db_session,
        user_id=user.id,
        insight_type=InsightType.SALARY_TREND,
    )
    assert insight.data["matches_analyzed"] == 0


@pytest.mark.asyncio
async def test_generate_market_insight_market_heat(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="heat@test.dev")
    await _make_job(db_session, title="Job A")
    await _make_job(db_session, title="Job B")

    insight = await analytics_service.generate_market_insight(
        db_session,
        user_id=user.id,
        insight_type=InsightType.MARKET_HEAT,
    )
    assert insight.data["total_period"] == 2
    assert isinstance(insight.data["daily_counts"], list)
    assert insight.data["average_per_day"] >= 0


@pytest.mark.asyncio
async def test_generate_market_insight_market_heat_empty(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="heat2@test.dev")
    insight = await analytics_service.generate_market_insight(
        db_session,
        user_id=user.id,
        insight_type=InsightType.MARKET_HEAT,
    )
    # Empty: daily_counts empty, average guarded by max(..., 1)
    assert insight.data["total_period"] == 0
    assert insight.data["average_per_day"] == 0.0
    assert insight.data["daily_counts"] == []


@pytest.mark.asyncio
async def test_generate_market_insight_competition(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="comp@test.dev")
    job = await _make_job(db_session, title="Comp Job")
    await _make_application(db_session, user_id=user.id, job_id=job.id)

    insight = await analytics_service.generate_market_insight(
        db_session,
        user_id=user.id,
        insight_type=InsightType.COMPETITION_LEVEL,
    )
    assert insight.data["your_applications"] == 1
    assert insight.data["estimated_competition"] == "moderate"


@pytest.mark.asyncio
async def test_generate_market_insight_competition_zero(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="compzero@test.dev")
    insight = await analytics_service.generate_market_insight(
        db_session,
        user_id=user.id,
        insight_type=InsightType.COMPETITION_LEVEL,
    )
    assert insight.data["your_applications"] == 0


@pytest.mark.asyncio
async def test_generate_market_insight_application_velocity(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="velo@test.dev")
    job1 = await _make_job(db_session, title="Velo Job 1")
    job2 = await _make_job(db_session, title="Velo Job 2")
    await _make_application(db_session, user_id=user.id, job_id=job1.id)
    await _make_application(db_session, user_id=user.id, job_id=job2.id)

    insight = await analytics_service.generate_market_insight(
        db_session,
        user_id=user.id,
        insight_type=InsightType.APPLICATION_VELOCITY,
    )
    assert insight.data["total"] == 2
    assert isinstance(insight.data["daily_applications"], list)
    assert insight.data["average_per_day"] >= 0


@pytest.mark.asyncio
async def test_generate_market_insight_application_velocity_empty(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="veloempty@test.dev")
    insight = await analytics_service.generate_market_insight(
        db_session,
        user_id=user.id,
        insight_type=InsightType.APPLICATION_VELOCITY,
    )
    assert insight.data["total"] == 0
    assert insight.data["average_per_day"] == 0.0
    assert insight.data["daily_applications"] == []


# ─────────────────────────────────────────────────────────────────────────
# get_market_insights
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_market_insights_returns_recent(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="list@test.dev")
    for itype in (InsightType.MARKET_HEAT, InsightType.COMPETITION_LEVEL):
        await analytics_service.generate_market_insight(
            db_session, user_id=user.id, insight_type=itype,
        )

    insights = await analytics_service.get_market_insights(
        db_session, user_id=user.id, limit=10,
    )
    assert len(insights) == 2
    assert all(i.user_id == user.id for i in insights)


@pytest.mark.asyncio
async def test_get_market_insights_respects_limit(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="limited@test.dev")
    for _ in range(3):
        await analytics_service.generate_market_insight(
            db_session, user_id=user.id,
            insight_type=InsightType.COMPETITION_LEVEL,
        )
    insights = await analytics_service.get_market_insights(
        db_session, user_id=user.id, limit=2,
    )
    assert len(insights) == 2


@pytest.mark.asyncio
async def test_get_market_insights_empty(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="listempty@test.dev")
    insights = await analytics_service.get_market_insights(
        db_session, user_id=user.id,
    )
    assert insights == []


# ─────────────────────────────────────────────────────────────────────────
# create_cv_experiment / record_experiment_result / get_experiments
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_cv_experiment(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="cv@test.dev")
    job = await _make_job(db_session, title="CV Job")
    resume = await _make_resume(db_session, user_id=user.id)
    variant_a = await _make_cv_version(
        db_session, resume_id=resume.id, job_id=job.id,
    )
    variant_b = await _make_cv_version(
        db_session, resume_id=resume.id, job_id=job.id,
    )

    experiment = await analytics_service.create_cv_experiment(
        db_session,
        user_id=user.id,
        job_listing_id=job.id,
        variant_a_id=variant_a.id,
        variant_b_id=variant_b.id,
        hypothesis="Variant B should outperform",
    )

    assert isinstance(experiment, CVExperiment)
    assert experiment.id is not None
    assert experiment.user_id == user.id
    assert experiment.hypothesis == "Variant B should outperform"
    assert experiment.status == ExperimentStatus.RUNNING


@pytest.mark.asyncio
async def test_create_cv_experiment_without_hypothesis(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="cvnohyp@test.dev")
    job = await _make_job(db_session, title="CV Job 2")
    resume = await _make_resume(db_session, user_id=user.id)
    a = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)
    b = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)

    experiment = await analytics_service.create_cv_experiment(
        db_session,
        user_id=user.id,
        job_listing_id=job.id,
        variant_a_id=a.id,
        variant_b_id=b.id,
    )
    assert experiment.hypothesis is None


@pytest.mark.asyncio
async def test_record_experiment_result_completes(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="rr@test.dev")
    job = await _make_job(db_session, title="RR Job")
    resume = await _make_resume(db_session, user_id=user.id)
    a = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)
    b = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)

    experiment = await analytics_service.create_cv_experiment(
        db_session,
        user_id=user.id,
        job_listing_id=job.id,
        variant_a_id=a.id,
        variant_b_id=b.id,
    )

    completed = await analytics_service.record_experiment_result(
        db_session,
        experiment_id=experiment.id,
        winner_id=a.id,
        metrics={"ctr_a": 0.1, "ctr_b": 0.05},
    )

    assert completed.winner_id == a.id
    assert completed.metrics == {"ctr_a": 0.1, "ctr_b": 0.05}
    assert completed.status == ExperimentStatus.COMPLETED
    assert completed.completed_at is not None


@pytest.mark.asyncio
async def test_record_experiment_result_defaults_empty_metrics(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="rrdef@test.dev")
    job = await _make_job(db_session, title="RR Job 2")
    resume = await _make_resume(db_session, user_id=user.id)
    a = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)
    b = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)

    experiment = await analytics_service.create_cv_experiment(
        db_session,
        user_id=user.id,
        job_listing_id=job.id,
        variant_a_id=a.id,
        variant_b_id=b.id,
    )
    completed = await analytics_service.record_experiment_result(
        db_session,
        experiment_id=experiment.id,
        winner_id=b.id,
    )
    assert completed.metrics == {}
    assert completed.winner_id == b.id


@pytest.mark.asyncio
async def test_record_experiment_result_not_found_raises(
    db_session: AsyncSession,
) -> None:
    bogus = uuid.uuid4()
    with pytest.raises(ValueError, match=f"Experiment {bogus} not found"):
        await analytics_service.record_experiment_result(
            db_session,
            experiment_id=bogus,
            winner_id=uuid.uuid4(),
        )


@pytest.mark.asyncio
async def test_get_experiments_returns_user_only(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="listexp@test.dev")
    other = await _make_user(db_session, email="other@test.dev")
    job = await _make_job(db_session, title="ListExp Job")
    resume = await _make_resume(db_session, user_id=user.id)
    a = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)
    b = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)

    await analytics_service.create_cv_experiment(
        db_session,
        user_id=user.id,
        job_listing_id=job.id,
        variant_a_id=a.id,
        variant_b_id=b.id,
    )
    await analytics_service.create_cv_experiment(
        db_session,
        user_id=other.id,
        job_listing_id=job.id,
        variant_a_id=a.id,
        variant_b_id=b.id,
    )

    results = await analytics_service.get_experiments(
        db_session, user_id=user.id,
    )
    assert len(results) == 1
    assert results[0].user_id == user.id


@pytest.mark.asyncio
async def test_get_experiments_respects_limit(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="explim@test.dev")
    job = await _make_job(db_session, title="Lim Job")
    resume = await _make_resume(db_session, user_id=user.id)
    a = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)
    b = await _make_cv_version(db_session, resume_id=resume.id, job_id=job.id)

    for _ in range(3):
        await analytics_service.create_cv_experiment(
            db_session,
            user_id=user.id,
            job_listing_id=job.id,
            variant_a_id=a.id,
            variant_b_id=b.id,
        )

    results = await analytics_service.get_experiments(
        db_session, user_id=user.id, limit=2,
    )
    assert len(results) == 2


@pytest.mark.asyncio
async def test_get_experiments_empty(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="expempty@test.dev")
    results = await analytics_service.get_experiments(
        db_session, user_id=user.id,
    )
    assert results == []


# ─────────────────────────────────────────────────────────────────────────
# Internal compute helpers — direct coverage
# ─────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_compute_skill_demand_no_matches(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="skempty@test.dev")
    cutoff = datetime.now(UTC) - timedelta(days=30)
    data = await analytics_service._compute_skill_demand(
        db_session, user.id, cutoff,
    )
    assert data["total_listings_analyzed"] == 0
    assert data["top_skills"] == []


@pytest.mark.asyncio
async def test_compute_skill_demand_null_description(
    db_session: AsyncSession,
) -> None:
    """Descriptions coerced to empty string when they are falsy."""
    user = await _make_user(db_session, email="sknull@test.dev")
    # description is NOT NULL in schema, but empty string still exercises the
    # `or ""` branch against a falsy value.
    job = await _make_job(db_session, description="")
    await _make_match(db_session, user_id=user.id, job_id=job.id)

    cutoff = datetime.now(UTC) - timedelta(days=30)
    data = await analytics_service._compute_skill_demand(
        db_session, user.id, cutoff,
    )
    assert data["total_listings_analyzed"] == 1
    assert data["top_skills"] == []


@pytest.mark.asyncio
async def test_compute_market_heat_average(db_session: AsyncSession) -> None:
    user = await _make_user(db_session, email="heatavg@test.dev")
    await _make_job(db_session, title="H1")
    await _make_job(db_session, title="H2")
    await _make_job(db_session, title="H3")

    cutoff = datetime.now(UTC) - timedelta(days=30)
    data = await analytics_service._compute_market_heat(
        db_session, user.id, cutoff,
    )
    assert data["total_period"] == 3
    # All jobs created today → 1 bucket of 3
    assert data["average_per_day"] == 3.0


@pytest.mark.asyncio
async def test_compute_application_velocity_average(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="velavg@test.dev")
    j1 = await _make_job(db_session, title="V1")
    j2 = await _make_job(db_session, title="V2")
    await _make_application(db_session, user_id=user.id, job_id=j1.id)
    await _make_application(db_session, user_id=user.id, job_id=j2.id)

    cutoff = datetime.now(UTC) - timedelta(days=30)
    data = await analytics_service._compute_application_velocity(
        db_session, user.id, cutoff,
    )
    assert data["total"] == 2
    assert data["average_per_day"] == 2.0


@pytest.mark.asyncio
async def test_compute_competition_level_isolated_per_user(
    db_session: AsyncSession,
) -> None:
    user = await _make_user(db_session, email="compiso@test.dev")
    other = await _make_user(db_session, email="compiso2@test.dev")
    job = await _make_job(db_session, title="Shared Job")
    await _make_application(db_session, user_id=user.id, job_id=job.id)
    # Create a job for the other user's app to avoid unique constraint
    job2 = await _make_job(db_session, title="Other Job")
    await _make_application(db_session, user_id=other.id, job_id=job2.id)

    cutoff = datetime.now(UTC) - timedelta(days=30)
    data = await analytics_service._compute_competition_level(
        db_session, user.id, cutoff,
    )
    assert data["your_applications"] == 1
