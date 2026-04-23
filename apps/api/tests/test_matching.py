"""
Unit tests for MatchingService.

Covers find_matches (embedding validation, DB query), explain_match (LLM call),
and store_match (DB persistence).
"""

from __future__ import annotations

import math
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.schemas import ParsedExperience, ParsedResume, ParsedSkill

# ── Helpers ───────────────────────────────────────────────────────


def _make_db_result(rows: list[dict]) -> MagicMock:
    """Create a mock SQLAlchemy result that returns given rows via mappings().all()."""
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    return result


def _make_resume() -> ParsedResume:
    return ParsedResume(
        full_name="Jane Doe",
        summary="Senior backend engineer",
        skills=[ParsedSkill(name="Python"), ParsedSkill(name="FastAPI")],
        experience=[ParsedExperience(title="Engineer", company="Acme")],
    )


# ── find_matches ──────────────────────────────────────────────────


class TestFindMatches:
    @pytest.mark.asyncio
    async def test_returns_match_candidates(self) -> None:
        from app.ai.matching import MatchingService
        from app.ai.schemas import MatchCandidate

        mock_db = AsyncMock()
        rows = [
            {"job_id": str(uuid.uuid4()), "title": "Backend Dev", "company": "Acme", "score": 0.92},
            {"job_id": str(uuid.uuid4()), "title": "Python Dev", "company": "Corp", "score": 0.85},
        ]
        mock_db.execute.return_value = _make_db_result(rows)

        result = await MatchingService.find_matches(
            mock_db,
            resume_embedding=[0.1, 0.2, 0.3],
            top_k=5,
        )

        assert len(result) == 2
        assert all(isinstance(c, MatchCandidate) for c in result)
        assert result[0].score == 0.92

    @pytest.mark.asyncio
    async def test_empty_result_returns_empty_list(self) -> None:
        from app.ai.matching import MatchingService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_db_result([])

        result = await MatchingService.find_matches(
            mock_db,
            resume_embedding=[0.1, 0.2],
            top_k=10,
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_nan_in_embedding_raises_value_error(self) -> None:
        from app.ai.matching import MatchingService

        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Non-finite"):
            await MatchingService.find_matches(
                mock_db,
                resume_embedding=[0.1, float("nan"), 0.3],
            )

    @pytest.mark.asyncio
    async def test_inf_in_embedding_raises_value_error(self) -> None:
        from app.ai.matching import MatchingService

        mock_db = AsyncMock()

        with pytest.raises(ValueError, match="Non-finite"):
            await MatchingService.find_matches(
                mock_db,
                resume_embedding=[0.1, float("inf"), 0.3],
            )

    @pytest.mark.asyncio
    async def test_embedding_sent_as_vector_string(self) -> None:
        from app.ai.matching import MatchingService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_db_result([])

        await MatchingService.find_matches(
            mock_db,
            resume_embedding=[0.5, -0.3, 0.1],
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]  # second positional arg is the params dict
        assert "[0.5,-0.3,0.1]" in params["embedding"]

    @pytest.mark.asyncio
    async def test_top_k_passed_to_query(self) -> None:
        from app.ai.matching import MatchingService

        mock_db = AsyncMock()
        mock_db.execute.return_value = _make_db_result([])

        await MatchingService.find_matches(
            mock_db,
            resume_embedding=[0.1],
            top_k=42,
        )

        call_args = mock_db.execute.call_args
        params = call_args[0][1]
        assert params["top_k"] == 42


# ── explain_match ─────────────────────────────────────────────────


class TestExplainMatch:
    @pytest.mark.asyncio
    async def test_returns_match_explanation(self) -> None:
        from app.ai.matching import MatchingService
        from app.ai.schemas import MatchExplanation

        data = {
            "overall_assessment": "Strong match with good alignment",
            "strengths": ["Python expertise", "API design"],
            "gaps": ["Kubernetes experience"],
            "recommendation": "strong_match",
        }

        with patch("app.ai.matching.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = data
            result = await MatchingService.explain_match(
                resume=_make_resume(),
                job_title="Senior Backend Engineer",
                job_company="TechCorp",
                job_description="Looking for Python experts.",
            )

        assert isinstance(result, MatchExplanation)
        assert result.recommendation == "strong_match"
        assert len(result.strengths) == 2

    @pytest.mark.asyncio
    async def test_skills_and_experience_in_prompt(self) -> None:
        from app.ai.matching import MatchingService

        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return {"overall_assessment": "Good", "recommendation": "good_match"}

        with patch("app.ai.matching.complete_json", side_effect=_capture):
            await MatchingService.explain_match(
                resume=_make_resume(),
                job_title="Dev",
                job_company="Corp",
                job_description="Job.",
            )

        assert "Python" in captured[0]
        assert "FastAPI" in captured[0]
        assert "Engineer at Acme" in captured[0]

    @pytest.mark.asyncio
    async def test_no_skills_shows_none_listed(self) -> None:
        from app.ai.matching import MatchingService

        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return {"overall_assessment": "Ok", "recommendation": "good_match"}

        resume = ParsedResume(full_name="John", summary="Dev", skills=[], experience=[])
        with patch("app.ai.matching.complete_json", side_effect=_capture):
            await MatchingService.explain_match(
                resume=resume,
                job_title="Dev",
                job_company="Corp",
                job_description="Job.",
            )

        assert "None listed" in captured[0]


# ── store_match ────────────────────────────────────────────────────


class TestStoreMatch:
    @pytest.mark.asyncio
    async def test_adds_and_flushes_match_result(self) -> None:
        from app.ai.matching import MatchingService

        mock_db = AsyncMock()
        user_id = uuid.uuid4()
        job_id = uuid.uuid4()

        result = await MatchingService.store_match(
            mock_db,
            user_id=user_id,
            job_id=job_id,
            score=0.87,
            explanation="Strong Python alignment",
        )

        mock_db.add.assert_called_once()
        mock_db.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_match_result_with_correct_fields(self) -> None:
        from app.ai.matching import MatchingService
        from app.models.matching import MatchResult

        mock_db = AsyncMock()
        user_id = uuid.uuid4()
        job_id = uuid.uuid4()

        result = await MatchingService.store_match(
            mock_db,
            user_id=user_id,
            job_id=job_id,
            score=0.75,
            explanation="Good skill overlap",
        )

        assert isinstance(result, MatchResult)
        assert result.overall_score == 0.75
        assert result.explanation == "Good skill overlap"
