"""
PathForge — Happy-Path & Error-Path Route Tests
================================================
Maximises statement coverage for:
  * app/api/v1/career_passport.py  (prefix /api/v1/career-passport)
  * app/api/v1/hidden_job_market.py (prefix /api/v1/hidden-job-market)

All service calls are mocked so tests run without a real AI backend.
The ``client`` fixture already overrides ``get_db`` with ``db_session``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.core.security import create_access_token, hash_password
from app.models.user import User

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.asyncio

# ── Helpers ────────────────────────────────────────────────────


async def _make_user(
    db: AsyncSession,
    email: str = "route-test@pathforge.eu",
) -> User:
    """Insert a minimal active/verified user for route-level tests."""
    user = User(
        email=email,
        hashed_password=hash_password("TestPass123!"),
        full_name="Route Tester",
        is_active=True,
        is_verified=True,
        auth_provider="email",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


def _auth_headers(user: User) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(str(user.id))}"}


# ── Shared mock data factories ─────────────────────────────────

_NOW = datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC)
_UID = uuid.uuid4
_CAREER_DNA_ID = uuid.uuid4()


def _credential_mapping_dict(user_id: uuid.UUID) -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": _CAREER_DNA_ID,
        "user_id": user_id,
        "source_qualification": "BSc Computer Science",
        "source_country": "Netherlands",
        "target_country": "Germany",
        "equivalent_level": "Bachelor",
        "eqf_level": "6",
        "recognition_notes": None,
        "framework_reference": None,
        "confidence_score": 0.85,
        "data_source": "AI",
        "disclaimer": "AI estimated.",
        "created_at": _NOW,
    }


def _country_comparison_dict(user_id: uuid.UUID) -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": _CAREER_DNA_ID,
        "user_id": user_id,
        "source_country": "Netherlands",
        "target_country": "Germany",
        "status": "active",
        "col_delta_pct": 5.0,
        "salary_delta_pct": 3.0,
        "purchasing_power_delta": -2.0,
        "tax_impact_notes": None,
        "market_demand_level": "high",
        "detailed_breakdown": None,
        "data_source": "AI",
        "disclaimer": "AI estimated.",
        "created_at": _NOW,
    }


def _visa_assessment_dict(user_id: uuid.UUID) -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": _CAREER_DNA_ID,
        "user_id": user_id,
        "nationality": "Dutch",
        "target_country": "Germany",
        "visa_type": "EU freedom of movement",
        "eligibility_score": 0.95,
        "requirements": None,
        "processing_time_weeks": None,
        "estimated_cost": None,
        "notes": None,
        "data_source": "AI",
        "disclaimer": "AI estimated.",
        "created_at": _NOW,
    }


def _market_demand_dict(user_id: uuid.UUID) -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": _CAREER_DNA_ID,
        "user_id": user_id,
        "country": "Netherlands",
        "role": "Software Engineer",
        "industry": "Technology",
        "demand_level": "high",
        "open_positions_estimate": 1000,
        "yoy_growth_pct": 8.5,
        "top_employers": None,
        "salary_range_min": 60000.0,
        "salary_range_max": 100000.0,
        "currency": "EUR",
        "data_source": "AI",
        "disclaimer": "AI estimated.",
        "created_at": _NOW,
    }


def _passport_score_dict() -> dict:
    return {
        "credential_score": 0.8,
        "visa_score": 0.9,
        "demand_score": 0.75,
        "financial_score": 0.7,
        "overall_score": 0.8,
        "target_country": "Germany",
    }


def _preference_dict(user_id: uuid.UUID) -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": _CAREER_DNA_ID,
        "preferred_countries": None,
        "nationality": "Dutch",
        "include_visa_info": True,
        "include_col_comparison": True,
        "include_market_demand": True,
        "created_at": _NOW,
    }


def _company_signal_dict(user_id: uuid.UUID) -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": _CAREER_DNA_ID,
        "user_id": user_id,
        "company_name": "Acme Corp",
        "signal_type": "hiring_surge",
        "title": "Rapid headcount expansion",
        "description": "50 new roles posted this month",
        "strength": 0.85,
        "source": "LinkedIn",
        "source_url": None,
        "status": "active",
        "confidence_score": 0.8,
        "detected_at": _NOW,
        "expires_at": None,
        "data_source": "AI",
        "disclaimer": "AI estimated.",
        "match_results": [],
        "outreach_templates": [],
        "hidden_opportunities": [],
        "created_at": _NOW,
    }


def _company_signal_summary_dict() -> dict:
    return {
        "id": uuid.uuid4(),
        "company_name": "Acme Corp",
        "signal_type": "hiring_surge",
        "title": "Rapid headcount expansion",
        "strength": 0.85,
        "status": "active",
        "confidence_score": 0.8,
        "detected_at": _NOW,
        "match_score": None,
    }


def _hjm_preference_dict(user_id: uuid.UUID) -> dict:
    return {
        "id": uuid.uuid4(),
        "career_dna_id": _CAREER_DNA_ID,
        "min_signal_strength": 0.5,
        "enabled_signal_types": None,
        "max_outreach_per_week": 5,
        "auto_generate_outreach": False,
        "notification_enabled": True,
        "created_at": _NOW,
    }


# ══════════════════════════════════════════════════════════════════
# CAREER PASSPORT TESTS
# ══════════════════════════════════════════════════════════════════


class TestCareerPassportDashboard:
    async def test_dashboard_happy_path_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /dashboard with empty data returns 200."""
        user = await _make_user(db_session, "cp-dashboard@pathforge.eu")
        dashboard_payload = {
            "credential_mappings": [],
            "country_comparisons": [],
            "visa_assessments": [],
            "market_demand": [],
            "preferences": None,
            "passport_scores": [],
        }
        with patch(
            "app.api.v1.career_passport.career_passport_service.get_dashboard",
            new=AsyncMock(return_value=dashboard_payload),
        ):
            resp = await client.get(
                "/api/v1/career-passport/dashboard",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["credential_mappings"] == []
        assert data["passport_scores"] == []
        assert data["preferences"] is None

    async def test_dashboard_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/career-passport/dashboard")
        assert resp.status_code == 401


# ── Full Passport Scan ─────────────────────────────────────────


class TestCareerPassportScan:
    async def test_scan_happy_path_billing_disabled(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /scan returns 201 when billing is disabled."""
        user = await _make_user(db_session, "cp-scan@pathforge.eu")
        scan_result = {
            "credential_mapping": _credential_mapping_dict(user.id),
            "country_comparison": _country_comparison_dict(user.id),
            "visa_assessment": _visa_assessment_dict(user.id),
            "market_demand": _market_demand_dict(user.id),
            "passport_score": _passport_score_dict(),
        }
        with (
            patch(
                "app.api.v1.career_passport.career_passport_service.full_passport_scan",
                new=AsyncMock(return_value=scan_result),
            ),
            patch("app.api.v1.career_passport.settings") as mock_settings,
            patch("app.core.feature_gate.get_user_tier", return_value="premium"),
        ):
            mock_settings.billing_enabled = False
            resp = await client.post(
                "/api/v1/career-passport/scan",
                headers=_auth_headers(user),
                json={
                    "source_qualification": "BSc Computer Science",
                    "source_country": "Netherlands",
                    "target_country": "Germany",
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["credential_mapping"]["source_qualification"] == "BSc Computer Science"

    async def test_scan_value_error_returns_404(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /scan with service ValueError → 404."""
        user = await _make_user(db_session, "cp-scan-err@pathforge.eu")
        with (
            patch(
                "app.api.v1.career_passport.career_passport_service.full_passport_scan",
                new=AsyncMock(side_effect=ValueError("Career DNA not found")),
            ),
            patch("app.api.v1.career_passport.settings") as mock_settings,
            patch("app.core.feature_gate.get_user_tier", return_value="premium"),
        ):
            mock_settings.billing_enabled = False
            resp = await client.post(
                "/api/v1/career-passport/scan",
                headers=_auth_headers(user),
                json={
                    "source_qualification": "BSc CS",
                    "source_country": "Netherlands",
                    "target_country": "Germany",
                },
            )
        assert resp.status_code == 404
        assert "Career DNA not found" in resp.json()["detail"]

    async def test_scan_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/career-passport/scan",
            json={
                "source_qualification": "BSc CS",
                "source_country": "Netherlands",
                "target_country": "Germany",
            },
        )
        assert resp.status_code == 401


# ── Credential Mapping ─────────────────────────────────────────


class TestCredentialMapping:
    async def test_create_credential_mapping_happy(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /credential-mapping returns 201 with response data."""
        user = await _make_user(db_session, "cp-cred-create@pathforge.eu")
        mapping_data = _credential_mapping_dict(user.id)
        with patch(
            "app.api.v1.career_passport.career_passport_service.map_credential",
            new=AsyncMock(return_value=mapping_data),
        ):
            resp = await client.post(
                "/api/v1/career-passport/credential-mapping",
                headers=_auth_headers(user),
                json={
                    "source_qualification": "BSc Computer Science",
                    "source_country": "Netherlands",
                    "target_country": "Germany",
                },
            )
        assert resp.status_code == 201
        assert resp.json()["source_country"] == "Netherlands"

    async def test_create_credential_mapping_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /credential-mapping with ValueError → 404."""
        user = await _make_user(db_session, "cp-cred-err@pathforge.eu")
        with patch(
            "app.api.v1.career_passport.career_passport_service.map_credential",
            new=AsyncMock(side_effect=ValueError("No Career DNA")),
        ):
            resp = await client.post(
                "/api/v1/career-passport/credential-mapping",
                headers=_auth_headers(user),
                json={
                    "source_qualification": "MBA",
                    "source_country": "Netherlands",
                    "target_country": "Germany",
                },
            )
        assert resp.status_code == 404

    async def test_get_credential_mapping_found(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /credential-mapping/{id} returns 200 when found."""
        user = await _make_user(db_session, "cp-cred-get@pathforge.eu")
        mapping_data = _credential_mapping_dict(user.id)
        mapping_id = mapping_data["id"]
        with patch(
            "app.api.v1.career_passport.career_passport_service.get_credential_mapping",
            new=AsyncMock(return_value=mapping_data),
        ):
            resp = await client.get(
                f"/api/v1/career-passport/credential-mapping/{mapping_id}",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        assert resp.json()["target_country"] == "Germany"

    async def test_get_credential_mapping_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /credential-mapping/{id} returns 404 when None."""
        user = await _make_user(db_session, "cp-cred-get404@pathforge.eu")
        with patch(
            "app.api.v1.career_passport.career_passport_service.get_credential_mapping",
            new=AsyncMock(return_value=None),
        ):
            resp = await client.get(
                f"/api/v1/career-passport/credential-mapping/{uuid.uuid4()}",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 404

    async def test_delete_credential_mapping_success(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """DELETE /credential-mapping/{id} returns 204 on success."""
        user = await _make_user(db_session, "cp-cred-del@pathforge.eu")
        with patch(
            "app.api.v1.career_passport.career_passport_service.delete_credential_mapping",
            new=AsyncMock(return_value=True),
        ):
            resp = await client.delete(
                f"/api/v1/career-passport/credential-mapping/{uuid.uuid4()}",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 204

    async def test_delete_credential_mapping_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """DELETE /credential-mapping/{id} returns 404 when not found."""
        user = await _make_user(db_session, "cp-cred-del404@pathforge.eu")
        with patch(
            "app.api.v1.career_passport.career_passport_service.delete_credential_mapping",
            new=AsyncMock(return_value=False),
        ):
            resp = await client.delete(
                f"/api/v1/career-passport/credential-mapping/{uuid.uuid4()}",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 404


# ── Country Comparison ─────────────────────────────────────────


class TestCountryComparison:
    async def test_create_country_comparison_happy(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /country-comparison returns 201."""
        user = await _make_user(db_session, "cp-cc@pathforge.eu")
        comparison_data = _country_comparison_dict(user.id)
        with patch(
            "app.api.v1.career_passport.career_passport_service.compare_countries",
            new=AsyncMock(return_value=comparison_data),
        ):
            resp = await client.post(
                "/api/v1/career-passport/country-comparison",
                headers=_auth_headers(user),
                json={"source_country": "Netherlands", "target_country": "Germany"},
            )
        assert resp.status_code == 201
        assert resp.json()["source_country"] == "Netherlands"

    async def test_create_country_comparison_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /country-comparison ValueError → 404."""
        user = await _make_user(db_session, "cp-cc-err@pathforge.eu")
        with patch(
            "app.api.v1.career_passport.career_passport_service.compare_countries",
            new=AsyncMock(side_effect=ValueError("No Career DNA")),
        ):
            resp = await client.post(
                "/api/v1/career-passport/country-comparison",
                headers=_auth_headers(user),
                json={"source_country": "Netherlands", "target_country": "Germany"},
            )
        assert resp.status_code == 404

    async def test_multi_country_comparison_happy(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /multi-country-comparison returns 201."""
        user = await _make_user(db_session, "cp-mcc@pathforge.eu")
        multi_result = {
            "comparisons": [],
            "passport_scores": [],
            "recommended_country": None,
            "recommendation_reasoning": None,
        }
        with patch(
            "app.api.v1.career_passport.career_passport_service.compare_multiple_countries",
            new=AsyncMock(return_value=multi_result),
        ):
            resp = await client.post(
                "/api/v1/career-passport/multi-country-comparison",
                headers=_auth_headers(user),
                json={
                    "source_country": "Netherlands",
                    "target_countries": ["Germany", "France"],
                },
            )
        assert resp.status_code == 201
        data = resp.json()
        assert data["comparisons"] == []
        assert data["recommended_country"] is None


# ── Visa Assessment ────────────────────────────────────────────


class TestVisaAssessment:
    async def test_create_visa_assessment_happy(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /visa-assessment returns 201."""
        user = await _make_user(db_session, "cp-visa@pathforge.eu")
        visa_data = _visa_assessment_dict(user.id)
        with patch(
            "app.api.v1.career_passport.career_passport_service.assess_visa",
            new=AsyncMock(return_value=visa_data),
        ):
            resp = await client.post(
                "/api/v1/career-passport/visa-assessment",
                headers=_auth_headers(user),
                json={"nationality": "Dutch", "target_country": "Germany"},
            )
        assert resp.status_code == 201
        assert resp.json()["visa_type"] == "EU freedom of movement"

    async def test_create_visa_assessment_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /visa-assessment ValueError → 404."""
        user = await _make_user(db_session, "cp-visa-err@pathforge.eu")
        with patch(
            "app.api.v1.career_passport.career_passport_service.assess_visa",
            new=AsyncMock(side_effect=ValueError("No Career DNA")),
        ):
            resp = await client.post(
                "/api/v1/career-passport/visa-assessment",
                headers=_auth_headers(user),
                json={"nationality": "Dutch", "target_country": "Germany"},
            )
        assert resp.status_code == 404


# ── Market Demand ──────────────────────────────────────────────


class TestMarketDemand:
    async def test_get_market_demand_empty(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /market-demand/{country} returns 200 with empty list."""
        user = await _make_user(db_session, "cp-mkt@pathforge.eu")
        with patch(
            "app.api.v1.career_passport.career_passport_service.get_market_demand_by_country",
            new=AsyncMock(return_value=[]),
        ):
            resp = await client.get(
                "/api/v1/career-passport/market-demand/Netherlands",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_get_market_demand_with_data(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /market-demand/{country} returns 200 with entries."""
        user = await _make_user(db_session, "cp-mkt2@pathforge.eu")
        demand_data = _market_demand_dict(user.id)
        with patch(
            "app.api.v1.career_passport.career_passport_service.get_market_demand_by_country",
            new=AsyncMock(return_value=[demand_data]),
        ):
            resp = await client.get(
                "/api/v1/career-passport/market-demand/Netherlands",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        entries = resp.json()
        assert len(entries) == 1
        assert entries[0]["country"] == "Netherlands"


# ── Preferences ────────────────────────────────────────────────


class TestCareerPassportPreferences:
    async def test_get_preferences_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /preferences returns 200 with null when no prefs."""
        user = await _make_user(db_session, "cp-pref-none@pathforge.eu")
        with patch(
            "app.api.v1.career_passport.career_passport_service.get_preferences",
            new=AsyncMock(return_value=None),
        ):
            resp = await client.get(
                "/api/v1/career-passport/preferences",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_get_preferences_with_data(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /preferences returns 200 with preference data."""
        user = await _make_user(db_session, "cp-pref@pathforge.eu")
        pref_data = _preference_dict(user.id)
        with patch(
            "app.api.v1.career_passport.career_passport_service.get_preferences",
            new=AsyncMock(return_value=pref_data),
        ):
            resp = await client.get(
                "/api/v1/career-passport/preferences",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        assert resp.json()["nationality"] == "Dutch"

    async def test_update_preferences_happy(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """PUT /preferences returns 200 with updated data."""
        user = await _make_user(db_session, "cp-pref-put@pathforge.eu")
        pref_data = _preference_dict(user.id)
        with patch(
            "app.api.v1.career_passport.career_passport_service.update_preferences",
            new=AsyncMock(return_value=pref_data),
        ):
            resp = await client.put(
                "/api/v1/career-passport/preferences",
                headers=_auth_headers(user),
                json={"nationality": "Dutch", "include_visa_info": True},
            )
        assert resp.status_code == 200
        assert resp.json()["include_visa_info"] is True

    async def test_update_preferences_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """PUT /preferences ValueError → 404."""
        user = await _make_user(db_session, "cp-pref-err@pathforge.eu")
        with patch(
            "app.api.v1.career_passport.career_passport_service.update_preferences",
            new=AsyncMock(side_effect=ValueError("No Career DNA")),
        ):
            resp = await client.put(
                "/api/v1/career-passport/preferences",
                headers=_auth_headers(user),
                json={"nationality": "Dutch"},
            )
        assert resp.status_code == 404


# ══════════════════════════════════════════════════════════════════
# HIDDEN JOB MARKET TESTS
# ══════════════════════════════════════════════════════════════════


class TestHiddenJobMarketDashboard:
    async def test_dashboard_empty_happy_path(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /hidden-job-market/dashboard returns 200 with empty data."""
        user = await _make_user(db_session, "hjm-dash@pathforge.eu")
        dashboard_payload = {
            "signals": [],
            "preferences": None,
            "total_signals": 0,
            "active_signals": 0,
            "matched_signals": 0,
            "dismissed_signals": 0,
            "total_opportunities": 0,
        }
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.get_dashboard",
            new=AsyncMock(return_value=dashboard_payload),
        ):
            resp = await client.get(
                "/api/v1/hidden-job-market/dashboard",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["signals"] == []
        assert data["total_signals"] == 0
        assert data["preferences"] is None

    async def test_dashboard_with_signals_and_preferences(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /hidden-job-market/dashboard returns 200 with populated data."""
        user = await _make_user(db_session, "hjm-dash2@pathforge.eu")
        pref_data = _hjm_preference_dict(user.id)
        summary = _company_signal_summary_dict()
        dashboard_payload = {
            "signals": [summary],
            "preferences": pref_data,
            "total_signals": 1,
            "active_signals": 1,
            "matched_signals": 0,
            "dismissed_signals": 0,
            "total_opportunities": 0,
        }
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.get_dashboard",
            new=AsyncMock(return_value=dashboard_payload),
        ):
            resp = await client.get(
                "/api/v1/hidden-job-market/dashboard",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_signals"] == 1
        assert data["preferences"] is not None

    async def test_dashboard_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/hidden-job-market/dashboard")
        assert resp.status_code == 401


# ── Scan Company ──────────────────────────────────────────────


class TestScanCompany:
    async def test_scan_company_happy_path(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /scan/company returns 201 with signal list."""
        user = await _make_user(db_session, "hjm-scan@pathforge.eu")
        signal_data = _company_signal_dict(user.id)
        with (
            patch(
                "app.api.v1.hidden_job_market.hidden_job_market_service.scan_company",
                new=AsyncMock(return_value=[signal_data]),
            ),
            patch("app.api.v1.hidden_job_market.settings") as mock_settings,
            patch("app.core.feature_gate.get_user_tier", return_value="premium"),
        ):
            mock_settings.billing_enabled = False
            resp = await client.post(
                "/api/v1/hidden-job-market/scan/company",
                headers=_auth_headers(user),
                json={"company_name": "Acme Corp", "industry": "Technology"},
            )
        assert resp.status_code == 201
        signals = resp.json()
        assert len(signals) == 1
        assert signals[0]["company_name"] == "Acme Corp"

    async def test_scan_company_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /scan/company ValueError → 404."""
        user = await _make_user(db_session, "hjm-scan-err@pathforge.eu")
        with (
            patch(
                "app.api.v1.hidden_job_market.hidden_job_market_service.scan_company",
                new=AsyncMock(side_effect=ValueError("No Career DNA")),
            ),
            patch("app.api.v1.hidden_job_market.settings") as mock_settings,
            patch("app.core.feature_gate.get_user_tier", return_value="premium"),
        ):
            mock_settings.billing_enabled = False
            resp = await client.post(
                "/api/v1/hidden-job-market/scan/company",
                headers=_auth_headers(user),
                json={"company_name": "Acme Corp"},
            )
        assert resp.status_code == 404

    async def test_scan_company_unauthenticated(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/hidden-job-market/scan/company",
            json={"company_name": "Acme Corp"},
        )
        assert resp.status_code == 401


# ── Preferences ────────────────────────────────────────────────


class TestHiddenJobMarketPreferences:
    async def test_get_preferences_none(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /preferences returns 200 with null when no prefs exist."""
        user = await _make_user(db_session, "hjm-pref-none@pathforge.eu")
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.get_preferences",
            new=AsyncMock(return_value=None),
        ):
            resp = await client.get(
                "/api/v1/hidden-job-market/preferences",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        assert resp.json() is None

    async def test_get_preferences_with_data(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /preferences returns 200 with preference data."""
        user = await _make_user(db_session, "hjm-pref@pathforge.eu")
        pref_data = _hjm_preference_dict(user.id)
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.get_preferences",
            new=AsyncMock(return_value=pref_data),
        ):
            resp = await client.get(
                "/api/v1/hidden-job-market/preferences",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        assert resp.json()["min_signal_strength"] == 0.5

    async def test_update_preferences_happy(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """PUT /preferences returns 200 with updated data."""
        user = await _make_user(db_session, "hjm-pref-put@pathforge.eu")
        pref_data = _hjm_preference_dict(user.id)
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.update_preferences",
            new=AsyncMock(return_value=pref_data),
        ):
            resp = await client.put(
                "/api/v1/hidden-job-market/preferences",
                headers=_auth_headers(user),
                json={"min_signal_strength": 0.6, "notification_enabled": True},
            )
        assert resp.status_code == 200
        assert resp.json()["notification_enabled"] is True

    async def test_update_preferences_value_error(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """PUT /preferences ValueError → 404."""
        user = await _make_user(db_session, "hjm-pref-err@pathforge.eu")
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.update_preferences",
            new=AsyncMock(side_effect=ValueError("No Career DNA")),
        ):
            resp = await client.put(
                "/api/v1/hidden-job-market/preferences",
                headers=_auth_headers(user),
                json={"min_signal_strength": 0.6},
            )
        assert resp.status_code == 404


# ── Opportunities ─────────────────────────────────────────────


class TestOpportunities:
    async def test_get_opportunities_happy(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /opportunities returns 200 with radar data."""
        user = await _make_user(db_session, "hjm-opp@pathforge.eu")
        radar_data = {
            "opportunities": [],
            "total_opportunities": 0,
            "top_industries": [],
            "avg_probability": 0.0,
        }
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.get_opportunity_radar",
            new=AsyncMock(return_value=radar_data),
        ):
            resp = await client.get(
                "/api/v1/hidden-job-market/opportunities",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_opportunities"] == 0
        assert data["opportunities"] == []

    async def test_get_opportunities_unauthenticated(
        self, client: AsyncClient
    ) -> None:
        resp = await client.get("/api/v1/hidden-job-market/opportunities")
        assert resp.status_code == 401


# ── Signal Detail ─────────────────────────────────────────────


class TestSignalDetail:
    async def test_get_signal_found(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /{signal_id} returns 200 when found."""
        user = await _make_user(db_session, "hjm-sig-get@pathforge.eu")
        signal_data = _company_signal_dict(user.id)
        signal_id = signal_data["id"]
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.get_signal",
            new=AsyncMock(return_value=signal_data),
        ):
            resp = await client.get(
                f"/api/v1/hidden-job-market/{signal_id}",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 200
        assert resp.json()["company_name"] == "Acme Corp"

    async def test_get_signal_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """GET /{signal_id} returns 404 when None."""
        user = await _make_user(db_session, "hjm-sig-404@pathforge.eu")
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.get_signal",
            new=AsyncMock(return_value=None),
        ):
            resp = await client.get(
                f"/api/v1/hidden-job-market/{uuid.uuid4()}",
                headers=_auth_headers(user),
            )
        assert resp.status_code == 404


# ── Dismiss Signal ────────────────────────────────────────────


class TestDismissSignal:
    async def test_dismiss_signal_happy(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /{signal_id}/dismiss returns 200 when found."""
        user = await _make_user(db_session, "hjm-dismiss@pathforge.eu")
        signal_data = _company_signal_dict(user.id)
        signal_id = signal_data["id"]
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.dismiss_signal",
            new=AsyncMock(return_value=signal_data),
        ):
            resp = await client.post(
                f"/api/v1/hidden-job-market/{signal_id}/dismiss",
                headers=_auth_headers(user),
                json={"action_taken": "dismissed", "reason": "Not relevant"},
            )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    async def test_dismiss_signal_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ) -> None:
        """POST /{signal_id}/dismiss returns 404 when None."""
        user = await _make_user(db_session, "hjm-dismiss-404@pathforge.eu")
        with patch(
            "app.api.v1.hidden_job_market.hidden_job_market_service.dismiss_signal",
            new=AsyncMock(return_value=None),
        ):
            resp = await client.post(
                f"/api/v1/hidden-job-market/{uuid.uuid4()}/dismiss",
                headers=_auth_headers(user),
                json={"action_taken": "dismissed"},
            )
        assert resp.status_code == 404
