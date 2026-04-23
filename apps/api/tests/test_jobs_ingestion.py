"""
PathForge — Job Ingestion Pipeline Tests
============================================
End-to-end tests for the ingestion orchestrator with mocked providers.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.jobs.dedup import compute_fingerprint
from app.jobs.providers.base import RawJobListing

# ── Fixtures ───────────────────────────────────────────────────


def _make_raw_listing(**kwargs) -> RawJobListing:
    """Create a RawJobListing with defaults."""
    defaults = {
        "title": "Python Developer",
        "company": "Acme Corp",
        "description": "Build awesome things with Python.",
        "location": "Amsterdam",
        "work_type": "full_time",
        "salary_info": "€60,000 - €80,000",
        "source_url": "https://example.com/job/1",
        "source_platform": "test",
        "external_id": "test-001",
    }
    defaults.update(kwargs)
    return RawJobListing(**defaults)


@pytest.fixture
def mock_provider():
    """Create a mock job provider."""
    provider = AsyncMock()
    provider.name = "test_provider"
    return provider


# ── Ingestion Pipeline Tests ───────────────────────────────────


class TestIngestionPipeline:
    """Test the full fetch → dedup → insert pipeline."""

    @pytest.mark.asyncio
    async def test_ingest_new_listings(self, mock_provider) -> None:
        """New listings should be inserted into DB."""
        from app.jobs.ingestion import ingest_jobs

        listings = [
            _make_raw_listing(title="Job A", external_id="a"),
            _make_raw_listing(title="Job B", external_id="b"),
        ]
        mock_provider.search = AsyncMock(return_value=listings)

        # Mock the DB operations
        with patch("app.jobs.ingestion._dedupe_and_insert", new_callable=AsyncMock) as mock_dedup:
            mock_dedup.return_value = (2, 0)  # 2 new, 0 dupes
            mock_session = AsyncMock()

            result = await ingest_jobs(
                session=mock_session,
                providers=[mock_provider],
                keywords="python",
            )

        assert result.total_fetched == 2
        assert result.total_new == 2
        assert result.total_duplicates == 0

    @pytest.mark.asyncio
    async def test_ingest_multi_provider(self, mock_provider) -> None:
        """Should aggregate results from multiple providers."""
        from app.jobs.ingestion import ingest_jobs

        provider1 = AsyncMock()
        provider1.name = "adzuna"
        provider1.search = AsyncMock(return_value=[
            _make_raw_listing(title="Job A", source_platform="adzuna"),
        ])

        provider2 = AsyncMock()
        provider2.name = "jooble"
        provider2.search = AsyncMock(return_value=[
            _make_raw_listing(title="Job B", source_platform="jooble"),
        ])

        with patch("app.jobs.ingestion._dedupe_and_insert", new_callable=AsyncMock) as mock_dedup:
            mock_dedup.return_value = (1, 0)
            mock_session = AsyncMock()

            result = await ingest_jobs(
                session=mock_session,
                providers=[provider1, provider2],
                keywords="python",
            )

        assert result.total_fetched == 2
        assert len(result.providers) == 2
        assert result.providers[0].provider == "adzuna"
        assert result.providers[1].provider == "jooble"

    @pytest.mark.asyncio
    async def test_ingest_provider_error_resilience(self) -> None:
        """Should handle provider errors gracefully."""
        from app.jobs.ingestion import ingest_jobs

        provider = AsyncMock()
        provider.name = "failing"
        provider.search = AsyncMock(side_effect=OSError("Network error"))

        with patch("app.jobs.ingestion._dedupe_and_insert", new_callable=AsyncMock) as mock_dedup:
            mock_dedup.return_value = (0, 0)
            mock_session = AsyncMock()

            result = await ingest_jobs(
                session=mock_session,
                providers=[provider],
                keywords="python",
            )

        assert result.total_fetched == 0
        assert result.providers[0].errors == 1


# ── Ingestion Stats Tests ─────────────────────────────────────


class TestIngestionStats:
    """Test IngestionStats and IngestionResult dataclasses."""

    def test_stats_to_dict(self) -> None:
        from app.jobs.ingestion import IngestionStats

        stats = IngestionStats(provider="adzuna", fetched=10, new=5, duplicates=5, errors=0)
        d = stats.to_dict()
        assert d["provider"] == "adzuna"
        assert d["fetched"] == 10
        assert d["new"] == 5

    def test_result_totals(self) -> None:
        from app.jobs.ingestion import IngestionResult, IngestionStats

        result = IngestionResult(providers=[
            IngestionStats(provider="adzuna", fetched=10, new=5, duplicates=5),
            IngestionStats(provider="jooble", fetched=8, new=3, duplicates=5),
        ])
        assert result.total_fetched == 18
        assert result.total_new == 8
        assert result.total_duplicates == 10


# ── Cross-Provider Dedup Tests ─────────────────────────────────


class TestCrossProviderDedup:
    """Test that deduplication works across providers."""

    def test_same_job_different_source(self) -> None:
        """Same job from Adzuna and Jooble should produce same fingerprint."""
        adzuna_listing = _make_raw_listing(
            title="Senior Python Developer",
            company="Tech Corp",
            location="Amsterdam, Netherlands",
            source_platform="adzuna",
        )
        jooble_listing = _make_raw_listing(
            title="Senior Python Developer",
            company="Tech Corp",
            location="Amsterdam, Netherlands",
            source_platform="jooble",
        )

        fp1 = compute_fingerprint(
            adzuna_listing.title, adzuna_listing.company, adzuna_listing.location
        )
        fp2 = compute_fingerprint(
            jooble_listing.title, jooble_listing.company, jooble_listing.location
        )
        assert fp1 == fp2

    def test_different_jobs_different_fingerprints(self) -> None:
        """Different jobs should have different fingerprints."""
        job_a = _make_raw_listing(title="Python Dev", company="Acme")
        job_b = _make_raw_listing(title="Java Dev", company="Acme")

        fp1 = compute_fingerprint(job_a.title, job_a.company, job_a.location)
        fp2 = compute_fingerprint(job_b.title, job_b.company, job_b.location)
        assert fp1 != fp2


# ── API Endpoint Tests ─────────────────────────────────────────


class TestIngestJobsEndpoint:
    """Test the ingest-jobs API endpoint."""

    @pytest.mark.asyncio
    async def test_ingest_no_providers_configured(
        self, client: AsyncClient, auth_headers: dict
    ) -> None:
        """Should return 400 when no providers are configured."""
        response = await client.post(
            "/api/v1/ai/ingest-jobs",
            json={"keywords": "python developer"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "No job providers configured" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_ingest_requires_auth(self, client: AsyncClient) -> None:
        """Should return 401 without auth."""
        response = await client.post(
            "/api/v1/ai/ingest-jobs",
            json={"keywords": "python developer"},
        )
        assert response.status_code == 401


# ── IngestionResult.to_dict ────────────────────────────────────


class TestIngestionResultToDict:
    def test_to_dict_includes_all_totals(self) -> None:
        from app.jobs.ingestion import IngestionResult, IngestionStats

        result = IngestionResult(providers=[
            IngestionStats(provider="adzuna", fetched=10, new=4, duplicates=6),
            IngestionStats(provider="jooble", fetched=5, new=2, duplicates=3),
        ])
        d = result.to_dict()
        assert d["total_fetched"] == 15
        assert d["total_new"] == 6
        assert d["total_duplicates"] == 9

    def test_to_dict_providers_list(self) -> None:
        from app.jobs.ingestion import IngestionResult, IngestionStats

        result = IngestionResult(providers=[
            IngestionStats(provider="adzuna", fetched=3, new=2, duplicates=1),
        ])
        d = result.to_dict()
        assert len(d["providers"]) == 1
        assert d["providers"][0]["provider"] == "adzuna"

    def test_to_dict_empty_result(self) -> None:
        from app.jobs.ingestion import IngestionResult

        d = IngestionResult().to_dict()
        assert d["total_fetched"] == 0
        assert d["total_new"] == 0
        assert d["total_duplicates"] == 0
        assert d["providers"] == []


# ── _dedupe_and_insert ─────────────────────────────────────────


@pytest.mark.asyncio
class TestDedupeAndInsert:
    """Direct tests for the private _dedupe_and_insert helper."""

    def _make_session(self, existing_fingerprints: list[str] | None = None) -> AsyncMock:
        """Return a mock AsyncSession that reports given fingerprints as existing."""
        from unittest.mock import MagicMock

        session = AsyncMock()
        existing = existing_fingerprints or []

        # fetchall() is synchronous on CursorResult — use MagicMock, not AsyncMock
        fp_result = MagicMock()
        fp_result.fetchall.return_value = [(fp,) for fp in existing]

        # INSERT result
        insert_result = MagicMock()

        session.execute.side_effect = [fp_result, insert_result]
        return session

    async def test_all_new_listings_inserted(self) -> None:
        from app.jobs.ingestion import _dedupe_and_insert

        listings = [_make_raw_listing(title=f"Job {i}", company="Acme") for i in range(3)]
        session = self._make_session(existing_fingerprints=[])

        with patch("app.jobs.ingestion.pg_insert") as mock_insert:
            mock_stmt = AsyncMock()
            mock_insert.return_value.values.return_value.on_conflict_do_nothing.return_value = mock_stmt
            new_count, dup_count = await _dedupe_and_insert(
                session=session, listings=listings
            )

        assert new_count == 3
        assert dup_count == 0
        session.commit.assert_called_once()

    async def test_all_existing_returns_zero_new(self) -> None:
        from unittest.mock import MagicMock

        from app.jobs.dedup import compute_fingerprint
        from app.jobs.ingestion import _dedupe_and_insert

        listing = _make_raw_listing(title="Dev", company="Acme", location="Amsterdam")
        fp = compute_fingerprint(listing.title, listing.company, listing.location)

        session = AsyncMock()
        fp_result = MagicMock()
        fp_result.fetchall.return_value = [(fp,)]
        session.execute.return_value = fp_result

        new_count, dup_count = await _dedupe_and_insert(
            session=session, listings=[listing]
        )

        assert new_count == 0
        assert dup_count == 1
        session.commit.assert_not_called()

    async def test_batch_internal_duplicates_counted(self) -> None:
        from app.jobs.ingestion import _dedupe_and_insert

        # Same job twice in the batch
        listing = _make_raw_listing(title="Dev", company="Acme", location="NL")
        session = self._make_session(existing_fingerprints=[])

        with patch("app.jobs.ingestion.pg_insert") as mock_insert:
            mock_stmt = AsyncMock()
            mock_insert.return_value.values.return_value.on_conflict_do_nothing.return_value = mock_stmt
            new_count, dup_count = await _dedupe_and_insert(
                session=session, listings=[listing, listing]
            )

        # 1 unique fingerprint → 1 new, 1 batch-internal dup
        assert new_count == 1
        assert dup_count == 1
