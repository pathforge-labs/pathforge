"""Tests for AIUsageService (T4 / Sprint 56, ADR-0008).

Aggregates `AITransparencyRecord` rows into per-engine, per-period
usage summaries. Cost is computed from token counts × model-price
table; the same record contributes to both the "scan count" view
(free tier) and the "EUR cost" view (premium tier) per the decision
default in `docs/architecture/sprint-55-58-code-side-readiness.md`
§12 (#4 = dual-display).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ai_transparency import AITransparencyRecord
from app.services.ai_usage_service import (
    EUR_PER_USD,
    AIUsageService,
    UsagePeriod,
)


def _make_record(
    *,
    user_id: uuid.UUID,
    analysis_type: str,
    model: str = "claude-sonnet-4-5",
    prompt_tokens: int = 1_000,
    completion_tokens: int = 500,
    latency_ms: int = 1_500,
    success: bool = True,
    created_at: datetime | None = None,
) -> AITransparencyRecord:
    return AITransparencyRecord(
        user_id=user_id,
        analysis_id=str(uuid.uuid4()),
        analysis_type=analysis_type,
        model=model,
        tier="primary",
        confidence_score=0.9,
        confidence_label="High",
        data_sources=[],
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
        success=success,
        retries=0,
        created_at=created_at or datetime.now(UTC),
    )


class TestAIUsageServiceEmpty:
    """No records → zero counts, zero cost, no per-engine rows."""

    @pytest.mark.asyncio
    async def test_summary_for_user_with_no_records(self, db_session: AsyncSession) -> None:
        service = AIUsageService(db_session)
        user_id = uuid.uuid4()

        summary = await service.summary(
            user_id=user_id,
            period=UsagePeriod.current_month(),
        )

        assert summary.total_calls == 0
        assert summary.total_cost_eur_cents == 0
        assert summary.engines == []


class TestAIUsageServiceAggregation:
    """Multiple records → per-engine aggregation with token + latency
    rollups."""

    @pytest.mark.asyncio
    async def test_groups_by_analysis_type(self, db_session: AsyncSession) -> None:
        service = AIUsageService(db_session)
        user_id = uuid.uuid4()

        # 3 calls in career_dna, 1 in threat_radar
        for _ in range(3):
            db_session.add(
                _make_record(
                    user_id=user_id,
                    analysis_type="career_dna",
                )
            )
        db_session.add(
            _make_record(
                user_id=user_id,
                analysis_type="threat_radar",
            )
        )
        await db_session.flush()

        summary = await service.summary(
            user_id=user_id,
            period=UsagePeriod.current_month(),
        )

        assert summary.total_calls == 4
        engines = {row.engine: row for row in summary.engines}
        assert engines["career_dna"].calls == 3
        assert engines["threat_radar"].calls == 1

    @pytest.mark.asyncio
    async def test_excludes_other_users(self, db_session: AsyncSession) -> None:
        service = AIUsageService(db_session)
        my_user = uuid.uuid4()
        other_user = uuid.uuid4()

        db_session.add(_make_record(user_id=my_user, analysis_type="career_dna"))
        db_session.add(_make_record(user_id=other_user, analysis_type="career_dna"))
        await db_session.flush()

        summary = await service.summary(
            user_id=my_user,
            period=UsagePeriod.current_month(),
        )

        assert summary.total_calls == 1

    @pytest.mark.asyncio
    async def test_filters_by_period(self, db_session: AsyncSession) -> None:
        service = AIUsageService(db_session)
        user_id = uuid.uuid4()

        now = datetime.now(UTC)
        last_month = now.replace(day=1) - timedelta(days=1)

        db_session.add(
            _make_record(
                user_id=user_id,
                analysis_type="career_dna",
                created_at=last_month,
            )
        )
        db_session.add(
            _make_record(
                user_id=user_id,
                analysis_type="career_dna",
                created_at=now,
            )
        )
        await db_session.flush()

        summary = await service.summary(
            user_id=user_id,
            period=UsagePeriod.current_month(),
        )

        assert summary.total_calls == 1


class TestAIUsageServiceCost:
    """Cost is derived from token counts × model price.  Free tier
    sees scan counts; premium tier sees EUR; the **same response**
    carries both fields (decision #4 = dual-display)."""

    @pytest.mark.asyncio
    async def test_cost_is_zero_for_zero_tokens(self, db_session: AsyncSession) -> None:
        service = AIUsageService(db_session)
        user_id = uuid.uuid4()

        db_session.add(
            _make_record(
                user_id=user_id,
                analysis_type="career_dna",
                prompt_tokens=0,
                completion_tokens=0,
            )
        )
        await db_session.flush()

        summary = await service.summary(
            user_id=user_id,
            period=UsagePeriod.current_month(),
        )

        assert summary.total_cost_eur_cents == 0

    @pytest.mark.asyncio
    async def test_cost_for_known_model(self, db_session: AsyncSession) -> None:
        service = AIUsageService(db_session)
        user_id = uuid.uuid4()

        # Sonnet ≈ $3 input + $15 output per 1M tokens. 10k input +
        # 5k output → $0.105 USD ≈ €0.099 (USD/EUR ~ 0.94).
        db_session.add(
            _make_record(
                user_id=user_id,
                analysis_type="career_dna",
                model="claude-sonnet-4-5",
                prompt_tokens=10_000,
                completion_tokens=5_000,
            )
        )
        await db_session.flush()

        summary = await service.summary(
            user_id=user_id,
            period=UsagePeriod.current_month(),
        )

        # Expected: (10000/1M * 300) + (5000/1M * 1500) cents-USD
        #         = 3 + 7.5 = 10.5 cents-USD
        # In EUR cents: 10.5 * EUR_PER_USD (~ 0.94) ≈ 9.87 cents
        # Round-trip integer cents:
        expected_usd_cents = Decimal("10.5")
        expected_eur_cents = int(
            (expected_usd_cents * Decimal(str(EUR_PER_USD))).to_integral_value()
        )
        assert summary.total_cost_eur_cents == expected_eur_cents

    @pytest.mark.asyncio
    async def test_cost_falls_back_for_unknown_model(self, db_session: AsyncSession) -> None:
        """Unknown model → record contributes to the call count but
        not to the cost total. The response carries a sentinel flag so
        the UI can warn 'cost estimate unavailable'.
        """
        service = AIUsageService(db_session)
        user_id = uuid.uuid4()

        db_session.add(
            _make_record(
                user_id=user_id,
                analysis_type="career_dna",
                model="custom-future-model-2027",
                prompt_tokens=10_000,
                completion_tokens=5_000,
            )
        )
        await db_session.flush()

        summary = await service.summary(
            user_id=user_id,
            period=UsagePeriod.current_month(),
        )

        assert summary.total_calls == 1
        assert summary.total_cost_eur_cents == 0
        assert summary.has_unpriced_models is True


class TestUsagePeriod:
    """Period helper produces (start, end) datetimes covering the
    requested window."""

    def test_current_month_includes_now(self) -> None:
        period = UsagePeriod.current_month()
        now = datetime.now(UTC)
        assert period.start <= now < period.end

    def test_current_month_starts_at_midnight_first_of_month(self) -> None:
        period = UsagePeriod.current_month()
        assert period.start.day == 1
        assert period.start.hour == 0
        assert period.start.minute == 0
        assert period.start.second == 0
