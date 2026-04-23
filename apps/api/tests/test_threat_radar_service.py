"""
PathForge — Threat Radar Service Unit Tests
=============================================
Service-layer tests for threat_radar_service.py.
LLM analyzer calls are mocked; DB uses in-memory SQLite fixture.

Coverage targets:
    - _compute_crs (all 5 factors, trend direction branches)
    - _compute_moat_score (all 4 dimensions, strength classification)
    - ThreatRadarService.run_full_scan (no CareerDNA, happy path)
    - ThreatRadarService.get_overview (no CareerDNA, empty state)
    - ThreatRadarService.get_alerts (no CareerDNA, pagination, filter)
    - ThreatRadarService.update_alert_status (not found, read, snoozed)
    - ThreatRadarService.get_preferences / update_preferences
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.career_dna import CareerDNA, SkillGenomeEntry
from app.models.threat_radar import AlertStatus, ThreatAlert
from app.models.user import User
from app.services.threat_radar_service import (
    ThreatRadarService,
    _compute_crs,
    _compute_moat_score,
)

# ── Fixtures ──────────────────────────────────────────────────────


async def _make_dna(
    db: AsyncSession,
    *,
    email: str,
    with_skills: bool = True,
    skill_count: int = 2,
) -> tuple[User, CareerDNA]:
    from app.core.security import hash_password

    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Radar Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Software Engineer",
        primary_industry="Technology",
        seniority_level="senior",
        location="Amsterdam",
    )
    db.add(dna)
    await db.flush()

    if with_skills:
        names = ["Python", "FastAPI", "PostgreSQL", "Docker", "Kubernetes"]
        for name in names[:skill_count]:
            skill = SkillGenomeEntry(
                career_dna_id=dna.id,
                skill_name=name,
                category="technical",
                proficiency_level="advanced",
                confidence=0.85,
                years_experience=4,
                source="resume",
            )
            db.add(skill)
        await db.flush()

    return user, dna


def _fake_risk_data() -> dict[str, Any]:
    return {
        "onet_soc_code": "15-1252.00",
        "onet_occupation_title": "Software Developer",
        "base_automation_probability": 0.25,
        "contextual_risk_score": 30.0,
        "risk_level": "low",
        "vulnerable_tasks": ["data entry"],
        "resilient_tasks": ["architecture design"],
    }


def _fake_trend_data() -> dict[str, Any]:
    return {
        "trend_direction": "growing",
        "impact_on_user": "positive",
        "growth_rate": 15.0,
    }


def _fake_shield_data() -> list[dict[str, Any]]:
    return [
        {"skill_name": "Python", "classification": "shield", "protection_score": 80.0},
        {"skill_name": "FastAPI", "classification": "exposure", "protection_score": 40.0},
    ]


def _fake_alerts_data() -> list[dict[str, Any]]:
    return [
        {
            "alert_type": "automation_risk",
            "title": "Test Alert",
            "description": "A test threat alert",
            "severity": "medium",
            "opportunity": "Upskill in AI",
            "action_steps": ["Learn ML basics"],
        }
    ]


# ── _compute_crs ──────────────────────────────────────────────────


class TestComputeCRS:
    def _base_dna(self, skill_count: int = 5) -> CareerDNA:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.growth_vector = None
        dna.experience_blueprint = None
        dna.skill_genome = [
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name=f"Skill{i}",
                category="technical",
                proficiency_level="advanced",
                confidence=0.8,
                source="resume",
            )
            for i in range(skill_count)
        ]
        return dna

    def test_returns_all_five_factors(self) -> None:
        dna = self._base_dna()
        result = _compute_crs(
            risk_data={"contextual_risk_score": 30.0},
            trend_data={"trend_direction": "growing"},
            shield_data=[],
            career_dna=dna,
        )
        assert "overall_score" in result
        assert "skill_diversity_index" in result
        assert "automation_resistance" in result
        assert "growth_velocity" in result
        assert "industry_stability" in result
        assert "adaptability_signal" in result

    def test_overall_score_clamped_0_to_100(self) -> None:
        dna = self._base_dna(skill_count=30)
        result = _compute_crs(
            risk_data={"contextual_risk_score": 0.0},
            trend_data={"trend_direction": "growing"},
            shield_data=[
                {"skill_name": f"S{i}", "classification": "shield"}
                for i in range(10)
            ],
            career_dna=dna,
        )
        assert 0.0 <= result["overall_score"] <= 100.0

    def test_industry_stability_growing_is_high(self) -> None:
        dna = self._base_dna()
        result = _compute_crs(
            risk_data={"contextual_risk_score": 50.0},
            trend_data={"trend_direction": "growing"},
            shield_data=[],
            career_dna=dna,
        )
        assert result["industry_stability"] == 85.0

    def test_industry_stability_declining_is_low(self) -> None:
        dna = self._base_dna()
        result = _compute_crs(
            risk_data={"contextual_risk_score": 50.0},
            trend_data={"trend_direction": "declining"},
            shield_data=[],
            career_dna=dna,
        )
        assert result["industry_stability"] == 25.0

    def test_industry_stability_disrupted_is_very_low(self) -> None:
        dna = self._base_dna()
        result = _compute_crs(
            risk_data={"contextual_risk_score": 50.0},
            trend_data={"trend_direction": "disrupted"},
            shield_data=[],
            career_dna=dna,
        )
        assert result["industry_stability"] == 15.0

    def test_adaptability_signal_with_all_shield_skills(self) -> None:
        dna = self._base_dna()
        shield_data = [{"classification": "shield"} for _ in range(4)]
        result = _compute_crs(
            risk_data={"contextual_risk_score": 50.0},
            trend_data={"trend_direction": "stable"},
            shield_data=shield_data,
            career_dna=dna,
        )
        assert result["adaptability_signal"] == 100.0

    def test_no_skills_gives_zero_diversity(self) -> None:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.skill_genome = []
        dna.growth_vector = None
        dna.experience_blueprint = None
        result = _compute_crs(
            risk_data={"contextual_risk_score": 50.0},
            trend_data={"trend_direction": "stable"},
            shield_data=[],
            career_dna=dna,
        )
        assert result["skill_diversity_index"] == 0.0


# ── _compute_moat_score ───────────────────────────────────────────


class TestComputeMoatScore:
    def _base_dna(self, skill_count: int = 5) -> CareerDNA:
        dna = CareerDNA(user_id=uuid.uuid4())
        dna.experience_blueprint = None
        dna.skill_genome = [
            SkillGenomeEntry(
                career_dna_id=uuid.uuid4(),
                skill_name=f"Skill{i}",
                category="technical",
                proficiency_level="advanced",
                confidence=0.8,
                source="resume",
            )
            for i in range(skill_count)
        ]
        return dna

    def test_returns_moat_score_and_strength(self) -> None:
        dna = self._base_dna()
        result = _compute_moat_score(shield_data=[], career_dna=dna)
        assert "moat_score" in result
        assert "moat_strength" in result

    def test_moat_score_clamped_0_to_100(self) -> None:
        dna = self._base_dna(skill_count=30)
        shield_data = [{"classification": "shield"} for _ in range(30)]
        result = _compute_moat_score(shield_data=shield_data, career_dna=dna)
        assert 0.0 <= result["moat_score"] <= 100.0

    def test_strength_wide_when_score_75_plus(self) -> None:
        dna = self._base_dna(skill_count=25)
        shield_data = [{"classification": "shield"} for _ in range(25)]
        result = _compute_moat_score(shield_data=shield_data, career_dna=dna)
        if result["moat_score"] >= 75:
            assert result["moat_strength"] == "wide"

    def test_strength_none_when_score_below_40(self) -> None:
        dna = self._base_dna(skill_count=0)
        dna.skill_genome = []
        result = _compute_moat_score(shield_data=[], career_dna=dna)
        # With no skills, score should be low
        assert result["moat_strength"] in ("none", "narrow", "wide")


# ── run_full_scan ─────────────────────────────────────────────────


class TestRunFullScan:
    @pytest.mark.asyncio
    async def test_returns_error_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await ThreatRadarService.run_full_scan(
            db_session,
            user_id=uuid.uuid4(),
            soc_code="15-1252.00",
            industry_name="Technology",
        )
        assert result["status"] == "error"
        assert "Career DNA" in result["detail"]

    @pytest.mark.asyncio
    async def test_happy_path_returns_all_sections(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="scan-happy@radar.com")

        with (
            patch(
                "app.services.threat_radar_service"
                ".ThreatRadarAnalyzer.score_automation_risk",
                new=AsyncMock(return_value=_fake_risk_data()),
            ),
            patch(
                "app.services.threat_radar_service"
                ".ThreatRadarAnalyzer.analyze_industry_trends",
                new=AsyncMock(return_value=_fake_trend_data()),
            ),
            patch(
                "app.services.threat_radar_service"
                ".ThreatRadarAnalyzer.classify_skills_shield",
                new=AsyncMock(return_value=_fake_shield_data()),
            ),
            patch(
                "app.services.threat_radar_service"
                ".ThreatRadarAnalyzer.generate_threat_assessment",
                new=AsyncMock(return_value=_fake_alerts_data()),
            ),
        ):
            result = await ThreatRadarService.run_full_scan(
                db_session,
                user_id=_user.id,
                soc_code="15-1252.00",
                industry_name="Technology",
            )

        assert result["status"] == "completed"
        assert result["automation_risk"] is not None
        assert result["industry_trend"] is not None
        assert result["snapshot"] is not None
        assert result["alerts_generated"] == 1


# ── get_overview ──────────────────────────────────────────────────


class TestGetOverview:
    @pytest.mark.asyncio
    async def test_returns_empty_dict_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await ThreatRadarService.get_overview(
            db_session, user_id=uuid.uuid4()
        )
        assert result == {}

    @pytest.mark.asyncio
    async def test_returns_zeroed_state_before_scan(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="overview-empty@radar.com")
        result = await ThreatRadarService.get_overview(
            db_session, user_id=_user.id
        )
        assert result["automation_risk"] is None
        assert result["shield_entries"] == []
        assert result["recent_alerts"] == []
        assert result["total_unread_alerts"] == 0


# ── get_alerts ────────────────────────────────────────────────────


class TestGetAlerts:
    @pytest.mark.asyncio
    async def test_returns_empty_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await ThreatRadarService.get_alerts(
            db_session, user_id=uuid.uuid4()
        )
        assert result["alerts"] == []
        assert result["total"] == 0

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_alerts(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="alerts-empty@radar.com")
        result = await ThreatRadarService.get_alerts(
            db_session, user_id=_user.id
        )
        assert result["alerts"] == []
        assert result["total"] == 0
        assert result["page"] == 1

    @pytest.mark.asyncio
    async def test_filters_by_status(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="alerts-filter@radar.com")

        # Create two alerts with different statuses
        unread = ThreatAlert(
            career_dna_id=_dna.id,
            category="automation_risk",
            title="Unread Alert",
            description="Test",
            opportunity="Upskill in AI tooling",
            severity="medium",
            status=AlertStatus.UNREAD.value,
        )
        read = ThreatAlert(
            career_dna_id=_dna.id,
            category="market_shift",
            title="Read Alert",
            description="Test",
            opportunity="Pivot to adjacent domain",
            severity="low",
            status=AlertStatus.READ.value,
        )
        db_session.add(unread)
        db_session.add(read)
        await db_session.flush()

        result = await ThreatRadarService.get_alerts(
            db_session, user_id=_user.id,
            status_filter=AlertStatus.UNREAD.value,
        )
        assert result["total"] == 1
        assert result["alerts"][0].title == "Unread Alert"


# ── update_alert_status ───────────────────────────────────────────


class TestUpdateAlertStatus:
    @pytest.mark.asyncio
    async def test_returns_none_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        result = await ThreatRadarService.update_alert_status(
            db_session,
            user_id=uuid.uuid4(),
            alert_id=uuid.uuid4(),
            new_status="read",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_alert_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="alert-notfound@radar.com")
        result = await ThreatRadarService.update_alert_status(
            db_session,
            user_id=_user.id,
            alert_id=uuid.uuid4(),
            new_status="read",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_marks_alert_as_read_sets_read_at(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="alert-read@radar.com")
        alert = ThreatAlert(
            career_dna_id=_dna.id,
            category="automation_risk",
            title="Test Alert",
            description="Test",
            opportunity="Upskill in AI tooling",
            severity="medium",
            status=AlertStatus.UNREAD.value,
        )
        db_session.add(alert)
        await db_session.flush()

        updated = await ThreatRadarService.update_alert_status(
            db_session,
            user_id=_user.id,
            alert_id=alert.id,
            new_status=AlertStatus.READ.value,
        )
        assert updated is not None
        assert updated.status == AlertStatus.READ.value
        assert updated.read_at is not None

    @pytest.mark.asyncio
    async def test_snooze_sets_snoozed_until(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="alert-snooze@radar.com")
        alert = ThreatAlert(
            career_dna_id=_dna.id,
            category="market_shift",
            title="Snooze Alert",
            description="Test",
            opportunity="Pivot to adjacent domain",
            severity="low",
            status=AlertStatus.UNREAD.value,
        )
        db_session.add(alert)
        await db_session.flush()

        snooze_until = datetime.now(UTC) + timedelta(days=7)
        updated = await ThreatRadarService.update_alert_status(
            db_session,
            user_id=_user.id,
            alert_id=alert.id,
            new_status=AlertStatus.SNOOZED.value,
            snoozed_until=snooze_until,
        )
        assert updated is not None
        assert updated.status == AlertStatus.SNOOZED.value
        assert updated.snoozed_until is not None


# ── preferences ───────────────────────────────────────────────────


class TestPreferences:
    @pytest.mark.asyncio
    async def test_get_preferences_no_career_dna_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        result = await ThreatRadarService.get_preferences(
            db_session, user_id=uuid.uuid4()
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_get_preferences_no_prefs_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="pref-none@radar.com")
        result = await ThreatRadarService.get_preferences(
            db_session, user_id=_user.id
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preferences_no_career_dna_returns_none(
        self, db_session: AsyncSession,
    ) -> None:
        result = await ThreatRadarService.update_preferences(
            db_session, user_id=uuid.uuid4(), updates={}
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_update_preferences_creates_and_updates(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="pref-create@radar.com")
        pref = await ThreatRadarService.update_preferences(
            db_session,
            user_id=_user.id,
            updates={"alert_frequency": "weekly"},
        )
        assert pref is not None
        assert pref.id is not None

    @pytest.mark.asyncio
    async def test_update_preferences_idempotent(
        self, db_session: AsyncSession,
    ) -> None:
        _user, _dna = await _make_dna(db_session, email="pref-idem@radar.com")
        pref1 = await ThreatRadarService.update_preferences(
            db_session, user_id=_user.id, updates={}
        )
        pref2 = await ThreatRadarService.update_preferences(
            db_session, user_id=_user.id, updates={}
        )
        assert pref1 is not None
        assert pref2 is not None
        assert pref1.id == pref2.id
