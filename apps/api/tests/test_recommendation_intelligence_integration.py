"""
PathForge — Cross-Engine Recommendation Intelligence™ Integration Tests
=========================================================================
Async integration tests for the RI service layer, exercising business
logic with a real (SQLite) async session.  Uses the ``db_session`` and
``authenticated_user`` fixtures from ``conftest.py``.

Coverage:
    - generate_recommendations pipeline (batch + recs + correlations)
    - update_recommendation_status transition state-machine
    - get_recommendation_detail  / list / correlations / batches
    - get_preferences / update_preferences  (upsert)
    - Error paths: not-found, invalid transitions
"""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.services.recommendation_intelligence_service import (
    RecommendationIntelligenceService as RIService,
)

# ── Generate Recommendations ──────────────────────────────────


@pytest.mark.asyncio
class TestGenerateRecommendations:
    """Integration tests for the recommendation generation pipeline."""

    async def test_generate_creates_batch_and_recommendations(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        batch = await RIService.generate_recommendations(
            db_session, user_id=authenticated_user.id,
        )
        assert batch.total_recommendations >= 1
        assert batch.batch_type == "manual"
        assert batch.engine_snapshot is not None

    async def test_generate_with_focus_categories(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        batch = await RIService.generate_recommendations(
            db_session,
            user_id=authenticated_user.id,
            focus_categories=["skill_gap"],
        )
        assert batch.total_recommendations >= 1

    async def test_generate_scheduled_batch_type(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        batch = await RIService.generate_recommendations(
            db_session,
            user_id=authenticated_user.id,
            batch_type="scheduled",
        )
        assert batch.batch_type == "scheduled"


# ── Status Transitions ────────────────────────────────────────


@pytest.mark.asyncio
class TestRecommendationStatusTransitions:
    """Validate the status transition state-machine."""

    async def _create_recommendation(
        self, db_session: AsyncSession, user_id: uuid.UUID,
    ) -> str:
        """Helper: generate a batch and return the first recommendation id."""
        await RIService.generate_recommendations(
            db_session, user_id=user_id,
        )
        recs = await RIService.list_recommendations(
            db_session, user_id=user_id,
        )
        assert len(recs) >= 1
        return str(recs[0].id)

    async def test_pending_to_in_progress(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        rec_id = await self._create_recommendation(
            db_session, authenticated_user.id,
        )
        updated = await RIService.update_recommendation_status(
            db_session,
            user_id=authenticated_user.id,
            recommendation_id=uuid.UUID(rec_id),
            new_status="in_progress",
        )
        assert updated.status == "in_progress"

    async def test_pending_to_dismissed(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        rec_id = await self._create_recommendation(
            db_session, authenticated_user.id,
        )
        updated = await RIService.update_recommendation_status(
            db_session,
            user_id=authenticated_user.id,
            recommendation_id=uuid.UUID(rec_id),
            new_status="dismissed",
        )
        assert updated.status == "dismissed"

    async def test_in_progress_to_completed(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        rec_id = await self._create_recommendation(
            db_session, authenticated_user.id,
        )
        await RIService.update_recommendation_status(
            db_session,
            user_id=authenticated_user.id,
            recommendation_id=uuid.UUID(rec_id),
            new_status="in_progress",
        )
        updated = await RIService.update_recommendation_status(
            db_session,
            user_id=authenticated_user.id,
            recommendation_id=uuid.UUID(rec_id),
            new_status="completed",
        )
        assert updated.status == "completed"

    async def test_invalid_transition_pending_to_completed_raises(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        rec_id = await self._create_recommendation(
            db_session, authenticated_user.id,
        )
        with pytest.raises(ValueError, match="Cannot transition"):
            await RIService.update_recommendation_status(
                db_session,
                user_id=authenticated_user.id,
                recommendation_id=uuid.UUID(rec_id),
                new_status="completed",
            )

    async def test_update_nonexistent_recommendation_raises(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        fake_id = uuid.uuid4()
        with pytest.raises(ValueError, match="not found"):
            await RIService.update_recommendation_status(
                db_session,
                user_id=authenticated_user.id,
                recommendation_id=fake_id,
                new_status="in_progress",
            )


# ── Detail / List / Correlations / Batches ────────────────────


@pytest.mark.asyncio
class TestRecommendationQueries:
    """Integration tests for read operations."""

    async def test_get_recommendation_detail(self, db_session: AsyncSession, authenticated_user: User) -> None:
        await RIService.generate_recommendations(
            db_session, user_id=authenticated_user.id,
        )
        recs = await RIService.list_recommendations(
            db_session, user_id=authenticated_user.id,
        )
        detail = await RIService.get_recommendation_detail(
            db_session,
            user_id=authenticated_user.id,
            recommendation_id=uuid.UUID(str(recs[0].id)),
        )
        assert detail is not None
        assert detail.title is not None

    async def test_list_recommendations_with_status_filter(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        await RIService.generate_recommendations(
            db_session, user_id=authenticated_user.id,
        )
        pending = await RIService.list_recommendations(
            db_session,
            user_id=authenticated_user.id,
            status_filter="pending",
        )
        assert all(rec.status == "pending" for rec in pending)

    async def test_get_correlations_for_recommendation(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        await RIService.generate_recommendations(
            db_session, user_id=authenticated_user.id,
        )
        recs = await RIService.list_recommendations(
            db_session, user_id=authenticated_user.id,
        )
        correlations = await RIService.get_correlations(
            db_session,
            user_id=authenticated_user.id,
            recommendation_id=uuid.UUID(str(recs[0].id)),
        )
        assert len(correlations) >= 1
        assert all(
            0.0 <= corr.correlation_strength <= 1.0 for corr in correlations
        )

    async def test_get_batches_returns_generated(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        await RIService.generate_recommendations(
            db_session, user_id=authenticated_user.id,
        )
        batches = await RIService.get_batches(
            db_session, user_id=authenticated_user.id,
        )
        assert len(batches) >= 1


# ── Dashboard ─────────────────────────────────────────────────


@pytest.mark.asyncio
class TestRecommendationDashboard:
    """Integration tests for the dashboard aggregation."""

    async def test_dashboard_returns_structure(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        dashboard = await RIService.get_dashboard(
            db_session, user_id=authenticated_user.id,
        )
        assert "total_pending" in dashboard
        assert "total_in_progress" in dashboard
        assert "total_completed" in dashboard


# ── Preferences ───────────────────────────────────────────────


@pytest.mark.asyncio
class TestRecommendationPreferences:
    """Integration tests for preference CRUD (upsert pattern)."""

    async def test_get_preferences_returns_none_when_empty(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        prefs = await RIService.get_preferences(
            db_session, user_id=authenticated_user.id,
        )
        assert prefs is None

    async def test_update_preferences_creates_new(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        updated = await RIService.update_preferences(
            db_session,
            user_id=authenticated_user.id,
            updates={"min_priority_threshold": 25.0},
        )
        assert updated.min_priority_threshold == 25.0

    async def test_update_preferences_upserts_existing(
        self, db_session: AsyncSession, authenticated_user: User,
    ) -> None:
        await RIService.update_preferences(
            db_session,
            user_id=authenticated_user.id,
            updates={"min_priority_threshold": 10.0},
        )
        updated = await RIService.update_preferences(
            db_session,
            user_id=authenticated_user.id,
            updates={"min_priority_threshold": 50.0},
        )
        assert updated.min_priority_threshold == 50.0
