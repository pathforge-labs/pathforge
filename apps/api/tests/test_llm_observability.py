"""
PathForge — AI Trust Layer™ Unit Tests
========================================
Tests for LLM observability, transparency infrastructure, and confidence scoring.
"""

from __future__ import annotations

import uuid

import pytest

from app.core.llm_observability import (
    CONFIDENCE_CAP,
    LLMMetricsCollector,
    TransparencyLog,
    TransparencyRecord,
    compute_confidence_score,
    confidence_label,
)

# ── LLMMetricsCollector Tests ──────────────────────────────────


class TestLLMMetricsCollector:
    """Tests for the in-memory metrics aggregator."""

    def test_records_successful_call(self) -> None:
        """Verify counters increment on success."""
        collector = LLMMetricsCollector()
        collector.record_call(
            model="test-model",
            tier="primary",
            latency_seconds=1.5,
            prompt_tokens=100,
            completion_tokens=200,
            success=True,
        )

        metrics = collector.get_metrics()
        assert metrics["global"]["total_calls"] == 1
        assert metrics["global"]["successful_calls"] == 1
        assert metrics["global"]["failed_calls"] == 0
        assert metrics["global"]["total_prompt_tokens"] == 100
        assert metrics["global"]["total_completion_tokens"] == 200
        assert metrics["global"]["total_tokens"] == 300
        assert metrics["global"]["success_rate"] == 100.0

    def test_records_failed_call(self) -> None:
        """Verify error tracking on failure."""
        collector = LLMMetricsCollector()
        collector.record_call(
            model="test-model",
            tier="primary",
            latency_seconds=2.0,
            success=False,
            error_type="TimeoutError",
        )

        metrics = collector.get_metrics()
        assert metrics["global"]["total_calls"] == 1
        assert metrics["global"]["successful_calls"] == 0
        assert metrics["global"]["failed_calls"] == 1
        assert metrics["global"]["success_rate"] == 0.0
        assert metrics["global"]["error_counts"]["TimeoutError"] == 1

    def test_aggregates_by_model_and_tier(self) -> None:
        """Verify per-model and per-tier breakdown."""
        collector = LLMMetricsCollector()

        collector.record_call(
            model="model-a", tier="primary",
            latency_seconds=1.0, success=True,
        )
        collector.record_call(
            model="model-b", tier="fast",
            latency_seconds=0.5, success=True,
        )
        collector.record_call(
            model="model-a", tier="primary",
            latency_seconds=1.2, success=True,
        )

        metrics = collector.get_metrics()
        assert metrics["by_model"]["model-a"]["total_calls"] == 2
        assert metrics["by_model"]["model-b"]["total_calls"] == 1
        assert metrics["by_tier"]["primary"]["total_calls"] == 2
        assert metrics["by_tier"]["fast"]["total_calls"] == 1
        assert metrics["global"]["total_calls"] == 3

    def test_reset_clears_all(self) -> None:
        """Verify clean slate after reset."""
        collector = LLMMetricsCollector()
        collector.record_call(
            model="test-model", tier="primary",
            latency_seconds=1.0, success=True,
        )
        collector.reset()

        metrics = collector.get_metrics()
        assert metrics["global"]["total_calls"] == 0
        assert metrics["by_model"] == {}
        assert metrics["by_tier"] == {}

    def test_avg_latency_excludes_failures(self) -> None:
        """Verify average latency only counts successful calls."""
        collector = LLMMetricsCollector()
        collector.record_call(
            model="m", tier="t", latency_seconds=2.0, success=True,
        )
        collector.record_call(
            model="m", tier="t", latency_seconds=5.0, success=False,
            error_type="Error",
        )

        metrics = collector.get_metrics()
        assert metrics["global"]["avg_latency_seconds"] == 2.0


# ── Confidence Score Tests ─────────────────────────────────────


class TestConfidenceScore:
    """Tests for the algorithmic confidence scoring."""

    def test_primary_tier_no_retries_fast(self) -> None:
        """Primary tier, no retries, fast response → high confidence."""
        score = compute_confidence_score(
            tier="primary",
            retries=0,
            latency_seconds=1.0,
            completion_tokens=500,
            max_tokens=4096,
        )
        assert score >= 0.90
        assert score <= CONFIDENCE_CAP

    def test_degraded_with_retries(self) -> None:
        """Multiple retries degrade confidence significantly."""
        score = compute_confidence_score(
            tier="primary",
            retries=2,
            latency_seconds=8.0,
            completion_tokens=500,
            max_tokens=4096,
        )
        # 1.0 * 0.75 * 0.85 = 0.6375
        assert score < 0.70

    def test_never_exceeds_cap(self) -> None:
        """Confidence must never exceed CONFIDENCE_CAP (0.95)."""
        score = compute_confidence_score(
            tier="primary",
            retries=0,
            latency_seconds=0.1,
            completion_tokens=100,
            max_tokens=4096,
        )
        assert score <= CONFIDENCE_CAP

    def test_truncation_penalty(self) -> None:
        """Near-max token usage penalizes confidence."""
        score_normal = compute_confidence_score(
            tier="primary", retries=0, latency_seconds=1.0,
            completion_tokens=2000, max_tokens=4096,
        )
        score_truncated = compute_confidence_score(
            tier="primary", retries=0, latency_seconds=1.0,
            completion_tokens=3950, max_tokens=4096,
        )
        assert score_truncated < score_normal

    def test_fast_tier_lower_than_primary(self) -> None:
        """Fast tier has lower baseline confidence than primary."""
        primary = compute_confidence_score(
            tier="primary", retries=0, latency_seconds=1.0,
            completion_tokens=500, max_tokens=4096,
        )
        fast = compute_confidence_score(
            tier="fast", retries=0, latency_seconds=1.0,
            completion_tokens=500, max_tokens=4096,
        )
        assert fast < primary

    def test_unknown_tier_uses_default(self) -> None:
        """Unknown tier gets a conservative default factor."""
        score = compute_confidence_score(
            tier="unknown", retries=0, latency_seconds=1.0,
            completion_tokens=500, max_tokens=4096,
        )
        assert score <= 0.85

    def test_high_latency_penalty(self) -> None:
        """Very high latency degrades confidence."""
        fast_score = compute_confidence_score(
            tier="primary", retries=0, latency_seconds=0.5,
            completion_tokens=500, max_tokens=4096,
        )
        slow_score = compute_confidence_score(
            tier="primary", retries=0, latency_seconds=15.0,
            completion_tokens=500, max_tokens=4096,
        )
        assert slow_score < fast_score


class TestConfidenceLabel:
    """Tests for confidence label conversion."""

    def test_high_label(self) -> None:
        assert confidence_label(0.90) == "High"

    def test_medium_label(self) -> None:
        assert confidence_label(0.70) == "Medium"

    def test_low_label(self) -> None:
        assert confidence_label(0.50) == "Low"

    def test_boundary_high(self) -> None:
        assert confidence_label(0.85) == "High"

    def test_boundary_medium(self) -> None:
        assert confidence_label(0.65) == "Medium"


# ── TransparencyRecord Tests ──────────────────────────────────


class TestTransparencyRecord:
    """Tests for the transparency record dataclass."""

    def test_auto_generates_id(self) -> None:
        """Each record gets a unique UUID."""
        record_a = TransparencyRecord(analysis_type="test.a")
        record_b = TransparencyRecord(analysis_type="test.b")
        assert record_a.analysis_id != record_b.analysis_id
        # Validate UUID format
        uuid.UUID(record_a.analysis_id)
        uuid.UUID(record_b.analysis_id)

    def test_to_dict_serialization(self) -> None:
        """Verify to_dict produces complete, JSON-safe output."""
        record = TransparencyRecord(
            analysis_type="career_dna.hidden_skills",
            model="test-model",
            tier="primary",
            confidence_score=0.87,
            confidence_label="High",
            data_sources=["experience_text", "skills_list"],
            prompt_tokens=100,
            completion_tokens=200,
            latency_ms=1500,
            success=True,
            retries=0,
        )
        data = record.to_dict()

        assert data["analysis_type"] == "career_dna.hidden_skills"
        assert data["model"] == "test-model"
        assert data["confidence_score"] == 0.87
        assert data["confidence_label"] == "High"
        assert data["tokens_used"] == 300
        assert data["data_sources"] == ["experience_text", "skills_list"]
        assert data["latency_ms"] == 1500
        assert data["success"] is True
        assert data["retries"] == 0

    def test_timestamp_auto_set(self) -> None:
        """Timestamp is auto-populated on creation."""
        record = TransparencyRecord()
        assert record.timestamp  # Not empty
        assert "T" in record.timestamp  # ISO format contains T separator


# ── TransparencyLog Tests ─────────────────────────────────────


class TestTransparencyLog:
    """Tests for the per-user circular buffer."""

    @pytest.mark.asyncio
    async def test_records_analysis(self) -> None:
        """Single record is stored and retrievable."""
        log = TransparencyLog()
        record = TransparencyRecord(analysis_type="test.record")
        log.record(user_id="user-1", entry=record)

        recent = await log.get_recent("user-1")
        assert len(recent) == 1
        assert recent[0].analysis_type == "test.record"

    @pytest.mark.asyncio
    async def test_get_by_id(self) -> None:
        """Records are findable by analysis_id."""
        log = TransparencyLog()
        record = TransparencyRecord(analysis_type="test.find")
        log.record(user_id="user-1", entry=record)

        found = await log.get_by_id(record.analysis_id)
        assert found is not None
        assert found.analysis_type == "test.find"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self) -> None:
        """Non-existent ID returns None."""
        log = TransparencyLog()
        assert await log.get_by_id("nonexistent") is None

    @pytest.mark.asyncio
    async def test_per_user_isolation(self) -> None:
        """Users only see their own records."""
        log = TransparencyLog()
        log.record(
            user_id="user-a",
            entry=TransparencyRecord(analysis_type="a.record"),
        )
        log.record(
            user_id="user-b",
            entry=TransparencyRecord(analysis_type="b.record"),
        )

        records_a = await log.get_recent("user-a")
        records_b = await log.get_recent("user-b")
        assert len(records_a) == 1
        assert len(records_b) == 1
        assert records_a[0].analysis_type == "a.record"
        assert records_b[0].analysis_type == "b.record"

    @pytest.mark.asyncio
    async def test_circular_buffer_cap(self) -> None:
        """Buffer evicts oldest records at capacity."""
        log = TransparencyLog()
        user_id = "test-user"

        # Fill beyond capacity
        for idx in range(210):
            log.record(
                user_id=user_id,
                entry=TransparencyRecord(analysis_type=f"analysis.{idx}"),
            )

        recent = await log.get_recent(user_id, limit=50)
        assert len(recent) <= 50

        # The oldest records (0-9) should have been evicted
        all_records = await log.get_recent(user_id, limit=200)
        analysis_types = {record.analysis_type for record in all_records}
        assert "analysis.0" not in analysis_types
        assert "analysis.209" in analysis_types

    @pytest.mark.asyncio
    async def test_newest_first_ordering(self) -> None:
        """get_recent returns newest records first."""
        log = TransparencyLog()
        for idx in range(5):
            log.record(
                user_id="user-1",
                entry=TransparencyRecord(analysis_type=f"test.{idx}"),
            )

        recent = await log.get_recent("user-1", limit=5)
        assert recent[0].analysis_type == "test.4"  # Newest
        assert recent[4].analysis_type == "test.0"  # Oldest

    @pytest.mark.asyncio
    async def test_limit_cap_at_50(self) -> None:
        """Limit parameter is capped at 50."""
        log = TransparencyLog()
        for idx in range(60):
            log.record(
                user_id="user-1",
                entry=TransparencyRecord(analysis_type=f"test.{idx}"),
            )

        recent = await log.get_recent("user-1", limit=100)
        assert len(recent) == 50

    @pytest.mark.asyncio
    async def test_get_user_for_analysis(self) -> None:
        """Can find which user owns an analysis."""
        log = TransparencyLog()
        record = TransparencyRecord(analysis_type="test.ownership")
        log.record(user_id="owner-user", entry=record)

        owner = await log.get_user_for_analysis(record.analysis_id)
        assert owner == "owner-user"

    @pytest.mark.asyncio
    async def test_get_user_for_analysis_not_found(self) -> None:
        """Returns None for unknown analysis IDs."""
        log = TransparencyLog()
        assert await log.get_user_for_analysis("nonexistent") is None

    def test_system_health_operational(self) -> None:
        """All successes → operational status."""
        log = TransparencyLog()
        for _ in range(5):
            log.record(
                user_id="user-1",
                entry=TransparencyRecord(
                    success=True, latency_ms=500,
                ),
            )

        health = log.get_system_health()
        assert health["system_status"] == "operational"
        assert health["success_rate"] == 100.0
        assert health["avg_latency_ms"] == 500.0
        assert health["total_analyses"] == 5
        assert health["active_users"] == 1
        assert health["pending_persistence_tasks"] >= 0
        assert health["persistence_failures"] == 0

    def test_system_health_degraded(self) -> None:
        """Mixed success rate → degraded status."""
        log = TransparencyLog()
        for idx in range(10):
            log.record(
                user_id="user-1",
                entry=TransparencyRecord(
                    success=idx < 9,  # 9/10 = 90% success
                    latency_ms=100,
                ),
            )

        health = log.get_system_health()
        assert health["system_status"] == "degraded"
        assert health["success_rate"] == 90.0

    def test_system_health_empty(self) -> None:
        """No records → operational with 100% success rate."""
        log = TransparencyLog()
        health = log.get_system_health()
        assert health["system_status"] == "operational"
        assert health["success_rate"] == 100.0
        assert health["total_analyses"] == 0
        assert health["last_analysis_at"] is None

    @pytest.mark.asyncio
    async def test_reset_clears_all(self) -> None:
        """Reset empties all records."""
        log = TransparencyLog()
        log.record(
            user_id="user-1",
            entry=TransparencyRecord(analysis_type="test.reset"),
        )
        log.reset()

        assert await log.get_recent("user-1") == []
        health = log.get_system_health()
        assert health["total_analyses"] == 0
        assert health["persistence_failures"] == 0
