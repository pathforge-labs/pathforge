"""
Unit tests for the job embedding pipeline.

Covers:
- job_to_canonical: all fields, optional fields, description truncation
- embed_new_jobs: no-op when empty, success path, batch failure resilience
"""

from __future__ import annotations

import sys
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.jobs.embed_pipeline import job_to_canonical

# ── Helpers ─────────────────────────────────────────────────────


def _make_job(**kwargs: Any) -> MagicMock:
    """Return a MagicMock shaped like a JobListing."""
    job = MagicMock()
    job.id = uuid.uuid4()
    job.title = kwargs.get("title", "Software Engineer")
    job.company = kwargs.get("company", "Acme Corp")
    job.location = kwargs.get("location", "Amsterdam, NL")
    job.work_type = kwargs.get("work_type", "remote")
    job.salary_info = kwargs.get("salary_info", "€80k–€100k")
    job.description = kwargs.get("description", "Build great things.")
    return job


def _make_embed_module(embed_batch_fn=None) -> MagicMock:
    """Return a mock for app.ai.embedding_service module."""
    mock_module = MagicMock()
    instance = mock_module.EmbeddingService.return_value
    if embed_batch_fn is not None:
        instance.embed_batch = embed_batch_fn
    return mock_module


# ── job_to_canonical ─────────────────────────────────────────────


class TestJobToCanonical:
    def test_all_fields_present(self) -> None:
        job = _make_job()
        text = job_to_canonical(job)
        assert "Title: Software Engineer" in text
        assert "Company: Acme Corp" in text
        assert "Location: Amsterdam, NL" in text
        assert "Type: remote" in text
        assert "Salary: €80k–€100k" in text
        assert "Description: Build great things." in text

    def test_no_location(self) -> None:
        job = _make_job(location=None)
        text = job_to_canonical(job)
        assert "Location:" not in text
        assert "Title:" in text

    def test_no_work_type(self) -> None:
        job = _make_job(work_type=None)
        text = job_to_canonical(job)
        assert "Type:" not in text

    def test_no_salary_info(self) -> None:
        job = _make_job(salary_info=None)
        text = job_to_canonical(job)
        assert "Salary:" not in text

    def test_no_description(self) -> None:
        job = _make_job(description=None)
        text = job_to_canonical(job)
        assert "Description:" not in text

    def test_description_truncated_at_2000_chars(self) -> None:
        long_desc = "x" * 5000
        job = _make_job(description=long_desc)
        text = job_to_canonical(job)
        # The embedded description must not exceed 2000 chars
        desc_line = next(l for l in text.splitlines() if l.startswith("Description:"))
        embedded_desc = desc_line[len("Description: "):]
        assert len(embedded_desc) == 2000

    def test_title_and_company_always_included(self) -> None:
        job = _make_job(
            title="Analyst",
            company="BigBank",
            location=None,
            work_type=None,
            salary_info=None,
            description=None,
        )
        text = job_to_canonical(job)
        lines = text.splitlines()
        assert lines[0] == "Title: Analyst"
        assert lines[1] == "Company: BigBank"
        assert len(lines) == 2

    def test_output_is_newline_joined(self) -> None:
        job = _make_job(location=None, work_type=None, salary_info=None, description=None)
        text = job_to_canonical(job)
        assert "\n" in text


# ── embed_new_jobs ────────────────────────────────────────────────


@pytest.mark.asyncio
class TestEmbedNewJobs:
    async def test_returns_zero_when_no_jobs(self) -> None:
        from app.jobs.embed_pipeline import embed_new_jobs

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute.return_value = mock_result

        mock_module = _make_embed_module(AsyncMock(return_value=[]))
        with patch.dict(sys.modules, {"app.ai.embedding_service": mock_module}):
            count = await embed_new_jobs(session=mock_session)

        assert count == 0
        mock_session.commit.assert_not_called()

    async def test_embeds_jobs_and_returns_count(self) -> None:
        from app.jobs.embed_pipeline import embed_new_jobs

        jobs = [_make_job(title=f"Job {i}") for i in range(3)]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = jobs
        mock_session.execute.return_value = mock_result

        fake_embeddings = [[0.1] * 768 for _ in jobs]
        mock_module = _make_embed_module(AsyncMock(return_value=fake_embeddings))

        with patch.dict(sys.modules, {"app.ai.embedding_service": mock_module}):
            count = await embed_new_jobs(session=mock_session, batch_size=10)

        assert count == 3
        mock_session.commit.assert_called_once()

    async def test_batch_exception_does_not_halt_other_batches(self) -> None:
        """If one batch fails, embedding continues with subsequent batches."""
        from app.jobs.embed_pipeline import embed_new_jobs

        jobs = [_make_job(title=f"Job {i}") for i in range(4)]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = jobs
        mock_session.execute.return_value = mock_result

        good_embeddings = [[0.0] * 768, [0.0] * 768]
        call_count = 0

        async def _flaky_embed(texts: list[str]) -> list[list[float]]:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Voyage API timeout")
            return good_embeddings

        mock_module = _make_embed_module(_flaky_embed)
        with patch.dict(sys.modules, {"app.ai.embedding_service": mock_module}):
            count = await embed_new_jobs(session=mock_session, batch_size=2)

        # First batch failed (0 embedded), second batch succeeded (2 embedded)
        assert count == 2
        mock_session.commit.assert_called_once()

    async def test_respects_batch_size(self) -> None:
        """embed_new_jobs calls embed_batch in chunks of batch_size."""
        from app.jobs.embed_pipeline import embed_new_jobs

        jobs = [_make_job() for _ in range(5)]
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = jobs
        mock_session.execute.return_value = mock_result

        batch_calls: list[int] = []

        async def _record_batch(texts: list[str]) -> list[list[float]]:
            batch_calls.append(len(texts))
            return [[0.0] * 768 for _ in texts]

        mock_module = _make_embed_module(_record_batch)
        with patch.dict(sys.modules, {"app.ai.embedding_service": mock_module}):
            await embed_new_jobs(session=mock_session, batch_size=2)

        # 5 jobs with batch_size=2 → batches of [2, 2, 1]
        assert batch_calls == [2, 2, 1]
        assert sum(batch_calls) == 5
