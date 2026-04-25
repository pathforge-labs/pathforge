"""
PathForge — Career Command Center™ & Recommendation Intelligence™ Route Tests
==============================================================================
Happy-path and error-path coverage for:
    * app/api/v1/career_command_center.py     (prefix: /api/v1/command-center)
    * app/api/v1/recommendation_intelligence.py (prefix: /api/v1/recommendations)

All service / cache calls are mocked so the suite exercises route-handler
bodies without hitting the real database-backed service layer.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio


# ── Helpers ───────────────────────────────────────────────────


async def _make_user(
    db: AsyncSession,
    email: str = "cmd@pathforge.eu",
) -> User:
    """Insert a minimal active/verified user."""
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name="Test",
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


# ── Stubs ─────────────────────────────────────────────────────


def _stub_snapshot_orm() -> MagicMock:
    """ORM-like object for CareerSnapshotResponse.model_validate()."""
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.user_id = uuid.uuid4()
    obj.career_dna_id = uuid.uuid4()
    obj.health_score = 72.0
    obj.health_band = "healthy"
    obj.engine_statuses = {}
    obj.strengths = None
    obj.attention_areas = None
    obj.trend_direction = "stable"
    obj.data_source = "Career Vitals™"
    obj.disclaimer = "AI estimate"
    obj.created_at = datetime.now(UTC)
    obj.updated_at = datetime.now(UTC)
    return obj


def _stub_health_summary() -> dict:
    return {
        "health_score": 72.0,
        "health_band": "healthy",
        "trend_direction": "stable",
        "engines_active": 8,
        "engines_total": 12,
        "top_strength": None,
        "top_attention": None,
    }


def _stub_pref_orm() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.user_id = uuid.uuid4()
    obj.pinned_engines = []
    obj.hidden_engines = []
    obj.created_at = datetime.now(UTC)
    obj.updated_at = datetime.now(UTC)
    return obj


def _stub_engine_detail() -> dict:
    return {
        "engine_name": "career_dna",
        "display_name": "Career DNA™",
        "heartbeat": "active",
        "score": 80.0,
        "last_updated": datetime.now(UTC),
        "record_count": 5,
        "recent_records": [],
        "data_source": "Career DNA™",
        "disclaimer": "AI estimate",
    }


def _stub_batch_orm() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.user_id = uuid.uuid4()
    obj.batch_type = "manual"
    obj.total_recommendations = 3
    obj.career_vitals_at_generation = 72.0
    obj.data_source = "Intelligence Fusion Engine™"
    obj.created_at = datetime.now(UTC)
    obj.updated_at = datetime.now(UTC)
    return obj


def _stub_rec_orm() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.user_id = uuid.uuid4()
    obj.batch_id = uuid.uuid4()
    obj.recommendation_type = "skill_gap"
    obj.status = "pending"
    obj.effort_level = "moderate"
    obj.priority_score = 70.0
    obj.urgency = 65.0
    obj.impact_score = 75.0
    obj.confidence_score = 0.75
    obj.title = "Improve Python skills"
    obj.description = "Focus on async Python."
    obj.action_items = ["Study asyncio"]
    obj.source_engines = ["skill_decay"]
    obj.data_source = "Intelligence Fusion Engine™"
    obj.disclaimer = "AI estimate"
    obj.created_at = datetime.now(UTC)
    obj.updated_at = datetime.now(UTC)
    return obj


def _stub_rec_pref_orm() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.user_id = uuid.uuid4()
    obj.enabled_categories = None
    obj.min_priority_threshold = 0.0
    obj.max_recommendations_per_batch = 10
    obj.preferred_effort_levels = None
    obj.notifications_enabled = True
    obj.created_at = datetime.now(UTC)
    obj.updated_at = datetime.now(UTC)
    return obj


def _stub_correlation_orm() -> MagicMock:
    obj = MagicMock()
    obj.id = uuid.uuid4()
    obj.recommendation_id = uuid.uuid4()
    obj.engine_name = "skill_decay"
    obj.correlation_strength = 0.8
    obj.insight_summary = "Skill freshness signals triggered this."
    obj.created_at = datetime.now(UTC)
    return obj


# ═══════════════════════════════════════════════════════════════
# CAREER COMMAND CENTER TESTS
# ═══════════════════════════════════════════════════════════════


class TestCommandCenterDashboard:
    """GET /api/v1/command-center/dashboard."""

    async def test_dashboard_returns_200_no_snapshot(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """When snapshot is None, dashboard returns 200 with empty engine list."""
        user = await _make_user(db_session, "ccc-dash-empty@pathforge.eu")
        headers = _auth_headers(user)

        with (
            patch(
                "app.api.v1.career_command_center.CareerCommandCenterService.get_dashboard",
                new=AsyncMock(return_value={"snapshot": None, "preferences": None}),
            ),
            patch(
                "app.api.v1.career_command_center.CareerCommandCenterService.get_health_summary",
                new=AsyncMock(return_value=_stub_health_summary()),
            ),
        ):
            response = await client.get(
                "/api/v1/command-center/dashboard", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["snapshot"] is None
        assert body["engine_statuses"] == []
        assert body["health_summary"]["health_score"] == 72.0

    async def test_dashboard_returns_200_with_snapshot(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """When snapshot has engine_statuses dict, engines are serialized."""
        user = await _make_user(db_session, "ccc-dash-full@pathforge.eu")
        headers = _auth_headers(user)
        snapshot = _stub_snapshot_orm()
        snapshot.engine_statuses = {
            "career_dna": {
                "display_name": "Career DNA™",
                "heartbeat": "active",
                "score": 80.0,
                "last_updated": None,
                "trend": "improving",
                "summary": "Great shape",
            }
        }

        with (
            patch(
                "app.api.v1.career_command_center.CareerCommandCenterService.get_dashboard",
                new=AsyncMock(
                    return_value={"snapshot": snapshot, "preferences": None}
                ),
            ),
            patch(
                "app.api.v1.career_command_center.CareerCommandCenterService.get_health_summary",
                new=AsyncMock(return_value=_stub_health_summary()),
            ),
        ):
            response = await client.get(
                "/api/v1/command-center/dashboard", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert len(body["engine_statuses"]) == 1
        assert body["engine_statuses"][0]["engine_name"] == "career_dna"

    async def test_dashboard_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/command-center/dashboard")
        assert response.status_code == 401


class TestCommandCenterHealthSummary:
    """GET /api/v1/command-center/health-summary."""

    async def test_health_summary_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-health@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.get_health_summary",
            new=AsyncMock(return_value=_stub_health_summary()),
        ):
            response = await client.get(
                "/api/v1/command-center/health-summary", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["health_band"] == "healthy"
        assert body["engines_active"] == 8

    async def test_health_summary_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-health-err@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.get_health_summary",
            new=AsyncMock(side_effect=ValueError("No career DNA found")),
        ):
            response = await client.get(
                "/api/v1/command-center/health-summary", headers=headers,
            )

        assert response.status_code == 400
        assert "No career DNA found" in response.json()["detail"]

    async def test_health_summary_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/command-center/health-summary")
        assert response.status_code == 401


class TestCommandCenterRefresh:
    """POST /api/v1/command-center/refresh."""

    async def test_refresh_returns_201_on_success(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-refresh-ok@pathforge.eu")
        headers = _auth_headers(user)
        snapshot = _stub_snapshot_orm()

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.refresh_snapshot",
            new=AsyncMock(return_value=snapshot),
        ):
            response = await client.post(
                "/api/v1/command-center/refresh", headers=headers,
            )

        assert response.status_code == 201
        assert response.json()["health_score"] == 72.0

    async def test_refresh_returns_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-refresh-err@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.refresh_snapshot",
            new=AsyncMock(side_effect=ValueError("Career DNA profile required")),
        ):
            response = await client.post(
                "/api/v1/command-center/refresh", headers=headers,
            )

        assert response.status_code == 400
        assert "Career DNA profile required" in response.json()["detail"]

    async def test_refresh_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post("/api/v1/command-center/refresh")
        assert response.status_code == 401


class TestCommandCenterEngineDetail:
    """GET /api/v1/command-center/engines/{engine_name}."""

    async def test_engine_detail_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-engine-ok@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.get_engine_detail",
            new=AsyncMock(return_value=_stub_engine_detail()),
        ):
            response = await client.get(
                "/api/v1/command-center/engines/career_dna", headers=headers,
            )

        assert response.status_code == 200
        assert response.json()["engine_name"] == "career_dna"

    async def test_engine_detail_returns_404_when_service_none(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-engine-404@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.get_engine_detail",
            new=AsyncMock(return_value=None),
        ):
            response = await client.get(
                "/api/v1/command-center/engines/career_dna", headers=headers,
            )

        assert response.status_code == 404

    async def test_engine_detail_returns_404_for_invalid_engine(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-engine-invalid@pathforge.eu")
        headers = _auth_headers(user)

        response = await client.get(
            "/api/v1/command-center/engines/nonexistent_engine", headers=headers,
        )

        assert response.status_code == 404
        assert "nonexistent_engine" in response.json()["detail"]

    async def test_engine_detail_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/command-center/engines/career_dna")
        assert response.status_code == 401


class TestCommandCenterPreferences:
    """GET and PUT /api/v1/command-center/preferences."""

    async def test_get_preferences_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-pref-get@pathforge.eu")
        headers = _auth_headers(user)
        pref = _stub_pref_orm()

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.get_preferences",
            new=AsyncMock(return_value=pref),
        ):
            response = await client.get(
                "/api/v1/command-center/preferences", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert "pinned_engines" in body

    async def test_get_preferences_returns_404_when_none(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-pref-get-404@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.get_preferences",
            new=AsyncMock(return_value=None),
        ):
            response = await client.get(
                "/api/v1/command-center/preferences", headers=headers,
            )

        assert response.status_code == 404
        assert "No preferences found" in response.json()["detail"]

    async def test_put_preferences_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-pref-put@pathforge.eu")
        headers = _auth_headers(user)
        pref = _stub_pref_orm()

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.update_preferences",
            new=AsyncMock(return_value=pref),
        ):
            response = await client.put(
                "/api/v1/command-center/preferences",
                headers=headers,
                json={"pinned_engines": ["career_dna"]},
            )

        assert response.status_code == 200

    async def test_put_preferences_returns_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "ccc-pref-put-err@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.career_command_center.CareerCommandCenterService.update_preferences",
            new=AsyncMock(side_effect=ValueError("Too many pinned engines")),
        ):
            response = await client.put(
                "/api/v1/command-center/preferences",
                headers=headers,
                json={"pinned_engines": ["career_dna"]},
            )

        assert response.status_code == 400
        assert "Too many pinned engines" in response.json()["detail"]

    async def test_preferences_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/command-center/preferences")
        assert response.status_code == 401


# ═══════════════════════════════════════════════════════════════
# RECOMMENDATION INTELLIGENCE TESTS
# ═══════════════════════════════════════════════════════════════

# The /generate endpoint uses require_feature("recommendation_intelligence").
# We bypass it by patching get_user_tier to "pro" so the gate passes.
_REC_FEATURE_GATE_PATCH = patch(
    "app.core.feature_gate.get_user_tier",
    return_value="pro",
)


class TestRecDashboard:
    """GET /api/v1/recommendations/dashboard."""

    async def test_dashboard_cache_miss_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Cache miss → service called → result cached and returned."""
        user = await _make_user(db_session, "rec-dash-miss@pathforge.eu")
        headers = _auth_headers(user)
        dashboard_data = {
            "latest_batch": None,
            "recent_recommendations": [],
            "total_pending": 2,
            "total_in_progress": 1,
            "total_completed": 5,
            "preferences": None,
        }

        with (
            patch(
                "app.api.v1.recommendation_intelligence.ic_cache"
            ) as mock_cache,
            patch(
                "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_dashboard",
                new=AsyncMock(return_value=dashboard_data),
            ),
        ):
            mock_cache.key.return_value = "rec_dash_k1"
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_cache.TTL_RECOMMENDATIONS = 300
            response = await client.get(
                "/api/v1/recommendations/dashboard", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["total_pending"] == 2
        assert body["latest_batch"] is None

    async def test_dashboard_cache_hit_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Cache hit → service not called, cached data returned directly."""
        user = await _make_user(db_session, "rec-dash-hit@pathforge.eu")
        headers = _auth_headers(user)
        cached_payload = {
            "latest_batch": None,
            "recent_recommendations": [],
            "total_pending": 0,
            "total_in_progress": 0,
            "total_completed": 0,
            "preferences": None,
        }

        with patch(
            "app.api.v1.recommendation_intelligence.ic_cache"
        ) as mock_cache:
            mock_cache.key.return_value = "rec_dash_k2"
            mock_cache.get = AsyncMock(return_value=cached_payload)
            response = await client.get(
                "/api/v1/recommendations/dashboard", headers=headers,
            )

        assert response.status_code == 200
        assert response.json()["total_pending"] == 0

    async def test_dashboard_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/recommendations/dashboard")
        assert response.status_code == 401


class TestRecGenerate:
    """POST /api/v1/recommendations/generate."""

    async def test_generate_returns_201_billing_disabled(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        """Billing disabled → skip limit check, generate, invalidate cache."""
        user = await _make_user(db_session, "rec-gen-ok@pathforge.eu")
        headers = _auth_headers(user)
        batch = _stub_batch_orm()

        with (
            _REC_FEATURE_GATE_PATCH,
            patch(
                "app.api.v1.recommendation_intelligence.settings"
            ) as mock_settings,
            patch(
                "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.generate_recommendations",
                new=AsyncMock(return_value=batch),
            ),
            patch(
                "app.api.v1.recommendation_intelligence.ic_cache"
            ) as mock_cache,
        ):
            mock_settings.billing_enabled = False
            mock_settings.rate_limit_career_dna = "10/minute"
            mock_cache.invalidate_user = AsyncMock()
            response = await client.post(
                "/api/v1/recommendations/generate",
                headers=headers,
                json={"batch_type": "manual"},
            )

        assert response.status_code == 201
        body = response.json()
        assert body["batch_type"] == "manual"
        assert body["total_recommendations"] == 3

    async def test_generate_returns_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-gen-err@pathforge.eu")
        headers = _auth_headers(user)

        with (
            _REC_FEATURE_GATE_PATCH,
            patch(
                "app.api.v1.recommendation_intelligence.settings"
            ) as mock_settings,
            patch(
                "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.generate_recommendations",
                new=AsyncMock(side_effect=ValueError("Career DNA required")),
            ),
            patch("app.api.v1.recommendation_intelligence.ic_cache"),
        ):
            mock_settings.billing_enabled = False
            mock_settings.rate_limit_career_dna = "10/minute"
            response = await client.post(
                "/api/v1/recommendations/generate",
                headers=headers,
                json={"batch_type": "manual"},
            )

        assert response.status_code == 400
        assert "Career DNA required" in response.json()["detail"]

    async def test_generate_requires_auth(self, client: AsyncClient) -> None:
        response = await client.post(
            "/api/v1/recommendations/generate",
            json={"batch_type": "manual"},
        )
        assert response.status_code == 401


class TestRecList:
    """GET /api/v1/recommendations/ — list endpoint (empty path)."""

    async def test_list_returns_empty_list(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-list-empty@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.list_recommendations",
            new=AsyncMock(return_value=[]),
        ):
            response = await client.get(
                "/api/v1/recommendations", headers=headers,
            )

        assert response.status_code == 200
        assert response.json() == []

    async def test_list_returns_recommendations(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-list-data@pathforge.eu")
        headers = _auth_headers(user)
        rec = _stub_rec_orm()

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.list_recommendations",
            new=AsyncMock(return_value=[rec]),
        ):
            response = await client.get(
                "/api/v1/recommendations", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["recommendation_type"] == "skill_gap"

    async def test_list_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/recommendations")
        assert response.status_code == 401


class TestRecDetail:
    """GET /api/v1/recommendations/{recommendation_id}."""

    async def test_detail_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-detail-ok@pathforge.eu")
        headers = _auth_headers(user)
        rec = _stub_rec_orm()
        rec_id = str(rec.id)

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_recommendation_detail",
            new=AsyncMock(return_value=rec),
        ):
            response = await client.get(
                f"/api/v1/recommendations/{rec_id}", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "pending"
        assert body["title"] == "Improve Python skills"

    async def test_detail_returns_404_when_none(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-detail-404@pathforge.eu")
        headers = _auth_headers(user)
        missing_id = str(uuid.uuid4())

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_recommendation_detail",
            new=AsyncMock(return_value=None),
        ):
            response = await client.get(
                f"/api/v1/recommendations/{missing_id}", headers=headers,
            )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    async def test_detail_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get(f"/api/v1/recommendations/{uuid.uuid4()}")
        assert response.status_code == 401


class TestRecUpdateStatus:
    """PUT /api/v1/recommendations/{recommendation_id}/status."""

    async def test_update_status_returns_200_and_invalidates_cache(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-upd-ok@pathforge.eu")
        headers = _auth_headers(user)
        rec = _stub_rec_orm()
        rec.status = "in_progress"
        rec_id = str(rec.id)

        with (
            patch(
                "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.update_recommendation_status",
                new=AsyncMock(return_value=rec),
            ),
            patch(
                "app.api.v1.recommendation_intelligence.ic_cache"
            ) as mock_cache,
        ):
            mock_cache.invalidate_user = AsyncMock()
            response = await client.put(
                f"/api/v1/recommendations/{rec_id}/status",
                headers=headers,
                json={"status": "in_progress"},
            )

        assert response.status_code == 200
        mock_cache.invalidate_user.assert_awaited_once()

    async def test_update_status_returns_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-upd-err@pathforge.eu")
        headers = _auth_headers(user)

        with (
            patch(
                "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.update_recommendation_status",
                new=AsyncMock(side_effect=ValueError("Invalid status transition")),
            ),
            patch("app.api.v1.recommendation_intelligence.ic_cache"),
        ):
            response = await client.put(
                f"/api/v1/recommendations/{uuid.uuid4()}/status",
                headers=headers,
                json={"status": "completed"},
            )

        assert response.status_code == 400
        assert "Invalid status transition" in response.json()["detail"]

    async def test_update_status_requires_auth(self, client: AsyncClient) -> None:
        response = await client.put(
            f"/api/v1/recommendations/{uuid.uuid4()}/status",
            json={"status": "completed"},
        )
        assert response.status_code == 401


class TestRecCorrelations:
    """GET /api/v1/recommendations/{recommendation_id}/correlations."""

    async def test_correlations_returns_list(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-corr-ok@pathforge.eu")
        headers = _auth_headers(user)
        corr = _stub_correlation_orm()
        rec_id = str(uuid.uuid4())

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_correlations",
            new=AsyncMock(return_value=[corr]),
        ):
            response = await client.get(
                f"/api/v1/recommendations/{rec_id}/correlations",
                headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["engine_name"] == "skill_decay"

    async def test_correlations_returns_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-corr-err@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_correlations",
            new=AsyncMock(side_effect=ValueError("Recommendation not found")),
        ):
            response = await client.get(
                f"/api/v1/recommendations/{uuid.uuid4()}/correlations",
                headers=headers,
            )

        assert response.status_code == 400

    async def test_correlations_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get(
            f"/api/v1/recommendations/{uuid.uuid4()}/correlations",
        )
        assert response.status_code == 401


class TestRecBatches:
    """GET /api/v1/recommendations/batches."""

    async def test_batches_returns_list(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-batches@pathforge.eu")
        headers = _auth_headers(user)
        batch = _stub_batch_orm()

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_batches",
            new=AsyncMock(return_value=[batch]),
        ):
            response = await client.get(
                "/api/v1/recommendations/batches", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert len(body) == 1
        assert body[0]["batch_type"] == "manual"

    async def test_batches_returns_empty_list(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-batches-empty@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_batches",
            new=AsyncMock(return_value=[]),
        ):
            response = await client.get(
                "/api/v1/recommendations/batches", headers=headers,
            )

        assert response.status_code == 200
        assert response.json() == []

    async def test_batches_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/recommendations/batches")
        assert response.status_code == 401


class TestRecPreferences:
    """GET and PUT /api/v1/recommendations/preferences."""

    async def test_get_preferences_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-pref-get@pathforge.eu")
        headers = _auth_headers(user)
        pref = _stub_rec_pref_orm()

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_preferences",
            new=AsyncMock(return_value=pref),
        ):
            response = await client.get(
                "/api/v1/recommendations/preferences", headers=headers,
            )

        assert response.status_code == 200
        body = response.json()
        assert body["notifications_enabled"] is True
        assert body["max_recommendations_per_batch"] == 10

    async def test_get_preferences_returns_404_when_none(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-pref-get-404@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.get_preferences",
            new=AsyncMock(return_value=None),
        ):
            response = await client.get(
                "/api/v1/recommendations/preferences", headers=headers,
            )

        assert response.status_code == 404
        assert "No preferences found" in response.json()["detail"]

    async def test_put_preferences_returns_200(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-pref-put@pathforge.eu")
        headers = _auth_headers(user)
        pref = _stub_rec_pref_orm()

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.update_preferences",
            new=AsyncMock(return_value=pref),
        ):
            response = await client.put(
                "/api/v1/recommendations/preferences",
                headers=headers,
                json={"notifications_enabled": False},
            )

        assert response.status_code == 200
        assert "notifications_enabled" in response.json()

    async def test_put_preferences_returns_400_on_value_error(
        self,
        client: AsyncClient,
        db_session: AsyncSession,
    ) -> None:
        user = await _make_user(db_session, "rec-pref-put-err@pathforge.eu")
        headers = _auth_headers(user)

        with patch(
            "app.api.v1.recommendation_intelligence.RecommendationIntelligenceService.update_preferences",
            new=AsyncMock(side_effect=ValueError("Invalid category")),
        ):
            response = await client.put(
                "/api/v1/recommendations/preferences",
                headers=headers,
                json={"enabled_categories": ["bad_type"]},
            )

        assert response.status_code == 400
        assert "Invalid category" in response.json()["detail"]

    async def test_preferences_requires_auth(self, client: AsyncClient) -> None:
        response = await client.get("/api/v1/recommendations/preferences")
        assert response.status_code == 401
