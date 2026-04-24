"""Extended tests for career_passport_service — covers uncovered functions."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.career_dna import CareerDNA
from app.models.career_passport import CredentialMapping
from app.models.user import User
from app.services.career_passport_service import (
    compare_multiple_countries,
    delete_credential_mapping,
    get_credential_mapping,
    get_market_demand_by_country,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────


async def _make_user_and_dna(db: AsyncSession, *, email: str) -> tuple[User, CareerDNA]:
    user = User(
        email=email,
        hashed_password=hash_password("Test1234!"),
        full_name="Passport Tester",
    )
    db.add(user)
    await db.flush()

    dna = CareerDNA(
        user_id=user.id,
        primary_role="Software Engineer",
        primary_industry="Technology",
        seniority_level="senior",
    )
    db.add(dna)
    await db.flush()
    return user, dna


async def _make_credential_mapping(
    db: AsyncSession, *, career_dna_id: uuid.UUID, user_id: uuid.UUID,
) -> CredentialMapping:
    mapping = CredentialMapping(
        career_dna_id=career_dna_id,
        user_id=user_id,
        source_qualification="BSc Computer Science",
        source_country="Turkey",
        target_country="Netherlands",
        equivalent_level="Bachelor's Degree",
        eqf_level="level_6",
        confidence_score=0.72,
    )
    db.add(mapping)
    await db.flush()
    return mapping


# ── get_credential_mapping ────────────────────────────────────────────────────


class TestGetCredentialMapping:
    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_credential_mapping(
            db_session,
            mapping_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_wrong_user(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(db_session, email="pp-get-cm@test.com")
        mapping = await _make_credential_mapping(
            db_session, career_dna_id=dna.id, user_id=user.id,
        )
        result = await get_credential_mapping(
            db_session,
            mapping_id=mapping.id,
            user_id=uuid.uuid4(),
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_mapping_for_correct_user(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(db_session, email="pp-get-cm-ok@test.com")
        mapping = await _make_credential_mapping(
            db_session, career_dna_id=dna.id, user_id=user.id,
        )
        result = await get_credential_mapping(
            db_session,
            mapping_id=mapping.id,
            user_id=user.id,
        )
        assert result is not None
        assert result.id == mapping.id
        assert result.target_country == "Netherlands"


# ── delete_credential_mapping ─────────────────────────────────────────────────


class TestDeleteCredentialMapping:
    @pytest.mark.asyncio
    async def test_returns_false_when_not_found(
        self, db_session: AsyncSession,
    ) -> None:
        result = await delete_credential_mapping(
            db_session,
            mapping_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_wrong_user(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(db_session, email="pp-del-cm-wrong@test.com")
        mapping = await _make_credential_mapping(
            db_session, career_dna_id=dna.id, user_id=user.id,
        )
        result = await delete_credential_mapping(
            db_session,
            mapping_id=mapping.id,
            user_id=uuid.uuid4(),
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_and_removes_record(
        self, db_session: AsyncSession,
    ) -> None:
        user, dna = await _make_user_and_dna(db_session, email="pp-del-cm-ok@test.com")
        mapping = await _make_credential_mapping(
            db_session, career_dna_id=dna.id, user_id=user.id,
        )
        mapping_id = mapping.id

        result = await delete_credential_mapping(
            db_session,
            mapping_id=mapping_id,
            user_id=user.id,
        )
        assert result is True

        gone = await get_credential_mapping(
            db_session,
            mapping_id=mapping_id,
            user_id=user.id,
        )
        assert gone is None


# ── compare_multiple_countries ────────────────────────────────────────────────


class TestCompareMultipleCountries:
    @pytest.mark.asyncio
    async def test_raises_when_more_than_5_countries(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Maximum 5"):
            await compare_multiple_countries(
                db_session,
                user_id=uuid.uuid4(),
                source_country="Netherlands",
                target_countries=["DE", "UK", "SE", "FR", "ES", "IT"],
            )

    @pytest.mark.asyncio
    async def test_raises_when_no_career_dna(
        self, db_session: AsyncSession,
    ) -> None:
        with pytest.raises(ValueError, match="Career DNA"):
            await compare_multiple_countries(
                db_session,
                user_id=uuid.uuid4(),
                source_country="Netherlands",
                target_countries=["Germany"],
            )

    @pytest.mark.asyncio
    async def test_happy_path_returns_scores(
        self, db_session: AsyncSession,
    ) -> None:
        user, _dna = await _make_user_and_dna(
            db_session, email="pp-multi@test.com",
        )

        fake_comparison_result = {
            "col_delta_pct": -5.0,
            "salary_delta_pct": 8.0,
            "purchasing_power_delta": 13.0,
            "market_demand_level": "high",
        }

        with patch(
            "app.services.career_passport_service"
            ".CareerPassportAnalyzer.analyze_country_comparison",
            new=AsyncMock(return_value=fake_comparison_result),
        ):
            result = await compare_multiple_countries(
                db_session,
                user_id=user.id,
                source_country="Netherlands",
                target_countries=["Germany", "Sweden"],
            )

        assert len(result["comparisons"]) == 2
        assert len(result["passport_scores"]) == 2
        assert result["recommended_country"] is not None


# ── get_market_demand_by_country ──────────────────────────────────────────────


class TestGetMarketDemandByCountry:
    @pytest.mark.asyncio
    async def test_returns_empty_when_none_exist(
        self, db_session: AsyncSession,
    ) -> None:
        result = await get_market_demand_by_country(
            db_session,
            country="Germany",
            user_id=uuid.uuid4(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_returns_only_entries_for_requested_country(
        self, db_session: AsyncSession,
    ) -> None:
        from app.models.career_passport import MarketDemandEntry

        user, dna = await _make_user_and_dna(
            db_session, email="pp-demand-country@test.com",
        )

        entry_de = MarketDemandEntry(
            career_dna_id=dna.id,
            user_id=user.id,
            country="Germany",
            role="Backend Engineer",
            demand_level="high",
        )
        entry_uk = MarketDemandEntry(
            career_dna_id=dna.id,
            user_id=user.id,
            country="United Kingdom",
            role="Backend Engineer",
            demand_level="moderate",
        )
        db_session.add(entry_de)
        db_session.add(entry_uk)
        await db_session.flush()

        result = await get_market_demand_by_country(
            db_session,
            country="Germany",
            user_id=user.id,
        )
        assert len(result) == 1
        assert result[0].country == "Germany"
