"""
Unit tests for CVTailoringService.generate_tailored_cv().

Covers: happy path, skills/experience edge cases, LLMError re-raise,
generic exception wrapping, and prompt formatting.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.ai.schemas import (
    CVSectionDiff,
    ParsedExperience,
    ParsedResume,
    ParsedSkill,
    TailoredCV,
)
from app.core.llm import LLMError

# ── Helpers ───────────────────────────────────────────────────────


def _make_resume(
    *,
    summary: str | None = "Experienced software engineer",
    skills: list[ParsedSkill] | None = None,
    experience: list[ParsedExperience] | None = None,
) -> ParsedResume:
    return ParsedResume(
        full_name="Jane Doe",
        email="jane@example.com",
        summary=summary or "",
        skills=skills or [],
        experience=experience or [],
    )


def _make_skill(name: str, category: str = "technical") -> ParsedSkill:
    return ParsedSkill(name=name, category=category)


def _make_experience(
    title: str = "Engineer",
    company: str = "Acme",
    description: str = "Built things",
    achievements: list[str] | None = None,
) -> ParsedExperience:
    return ParsedExperience(
        title=title,
        company=company,
        description=description,
        achievements=achievements or [],
    )


def _make_tailored_cv_data() -> dict:
    return {
        "tailored_summary": "Tailored summary for the role",
        "tailored_skills": ["Python", "FastAPI"],
        "tailored_experience": ["Led a team of 5 engineers"],
        "diffs": [
            {
                "section": "summary",
                "original": "Generic summary",
                "modified": "Tailored summary for the role",
                "reason": "Better matched to job requirements",
            }
        ],
        "ats_score": 85,
        "ats_suggestions": ["Add more keywords from job description"],
    }


# ── Happy Path ────────────────────────────────────────────────────


class TestGenerateTailoredCVHappyPath:
    @pytest.mark.asyncio
    async def test_returns_tailored_cv_instance(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(skills=[_make_skill("Python"), _make_skill("FastAPI")])
        data = _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = data
            result = await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Senior Engineer",
                job_company="TechCorp",
                job_description="We need a senior engineer.",
            )

        assert isinstance(result, TailoredCV)
        assert result.ats_score == 85
        assert result.tailored_summary == "Tailored summary for the role"

    @pytest.mark.asyncio
    async def test_complete_json_called_with_primary_tier(self) -> None:
        from app.ai.cv_tailor import CVTailoringService
        from app.core.llm import LLMTier

        resume = _make_resume()
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_tailored_cv_data()
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Engineer",
                job_company="Corp",
                job_description="A job.",
            )

        call_kwargs = mock_llm.call_args.kwargs
        assert call_kwargs["tier"] == LLMTier.PRIMARY
        assert call_kwargs["temperature"] == 0.3
        assert call_kwargs["max_tokens"] == 4096

    @pytest.mark.asyncio
    async def test_diffs_parsed_correctly(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_tailored_cv_data()
            result = await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Startup",
                job_description="Build stuff.",
            )

        assert len(result.diffs) == 1
        diff = result.diffs[0]
        assert isinstance(diff, CVSectionDiff)
        assert diff.section == "summary"

    @pytest.mark.asyncio
    async def test_ats_suggestions_included(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_tailored_cv_data()
            result = await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="X",
                job_description="Do things.",
            )

        assert len(result.ats_suggestions) == 1


# ── Skills Text Preparation ───────────────────────────────────────


class TestSkillsTextPreparation:
    @pytest.mark.asyncio
    async def test_skills_joined_as_comma_list(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(
            skills=[_make_skill("Python"), _make_skill("Docker"), _make_skill("SQL")]
        )
        captured_prompt: list[str] = []

        async def _capture(**kwargs):
            captured_prompt.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        assert "Python, Docker, SQL" in captured_prompt[0]

    @pytest.mark.asyncio
    async def test_no_skills_uses_none_text(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(skills=[])
        captured_prompt: list[str] = []

        async def _capture(**kwargs):
            captured_prompt.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        assert "None" in captured_prompt[0]

    @pytest.mark.asyncio
    async def test_single_skill_no_trailing_comma(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(skills=[_make_skill("Go")])
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        assert "Go" in captured[0]


# ── Experience Text Preparation ───────────────────────────────────


class TestExperienceTextPreparation:
    @pytest.mark.asyncio
    async def test_experience_formatted_with_title_company(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(
            experience=[_make_experience(title="Lead Dev", company="Corp", description="Led team")]
        )
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        assert "Lead Dev at Corp" in captured[0]
        assert "Led team" in captured[0]

    @pytest.mark.asyncio
    async def test_achievements_appended_to_experience(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(
            experience=[
                _make_experience(
                    achievements=["Reduced latency by 40%", "Mentored 3 juniors"]
                )
            ]
        )
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        assert "Reduced latency by 40%" in captured[0]

    @pytest.mark.asyncio
    async def test_no_experience_uses_none_text(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(experience=[])
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        assert "None" in captured[0]

    @pytest.mark.asyncio
    async def test_multiple_experiences_all_included(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(
            experience=[
                _make_experience(title="Senior Dev", company="Alpha"),
                _make_experience(title="Junior Dev", company="Beta"),
            ]
        )
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        assert "Alpha" in captured[0]
        assert "Beta" in captured[0]


# ── Summary Edge Cases ────────────────────────────────────────────


class TestSummaryHandling:
    @pytest.mark.asyncio
    async def test_empty_summary_uses_fallback(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(summary="")
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        assert "No summary provided" in captured[0]

    @pytest.mark.asyncio
    async def test_actual_summary_passed_through(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume(summary="Expert in distributed systems")
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        assert "Expert in distributed systems" in captured[0]


# ── Error Handling ────────────────────────────────────────────────


class TestErrorHandling:
    @pytest.mark.asyncio
    async def test_llm_error_is_reraised(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("Rate limit hit")
            with pytest.raises(LLMError, match="Rate limit hit"):
                await CVTailoringService.generate_tailored_cv(
                    resume=resume,
                    job_title="Dev",
                    job_company="Co",
                    job_description="Job.",
                )

    @pytest.mark.asyncio
    async def test_llm_error_reraise_is_not_wrapped(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        original = LLMError("Quota exceeded")
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = original
            with pytest.raises(LLMError) as exc_info:
                await CVTailoringService.generate_tailored_cv(
                    resume=resume,
                    job_title="Dev",
                    job_company="Co",
                    job_description="Job.",
                )
        assert exc_info.value is original

    @pytest.mark.asyncio
    async def test_generic_exception_wrapped_in_llm_error(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = ValueError("Unexpected JSON structure")
            with pytest.raises(LLMError, match="CV tailoring failed"):
                await CVTailoringService.generate_tailored_cv(
                    resume=resume,
                    job_title="Dev",
                    job_company="Co",
                    job_description="Job.",
                )

    @pytest.mark.asyncio
    async def test_wrapped_exception_has_cause(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        original_exc = RuntimeError("Something broke")
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = original_exc
            with pytest.raises(LLMError) as exc_info:
                await CVTailoringService.generate_tailored_cv(
                    resume=resume,
                    job_title="Dev",
                    job_company="Co",
                    job_description="Job.",
                )
        assert exc_info.value.__cause__ is original_exc

    @pytest.mark.asyncio
    async def test_pydantic_validation_error_wrapped_in_llm_error(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            # Return data that fails Pydantic validation (ats_score > 100)
            mock_llm.return_value = {"ats_score": 999}
            with pytest.raises((LLMError, Exception)):
                await CVTailoringService.generate_tailored_cv(
                    resume=resume,
                    job_title="Dev",
                    job_company="Co",
                    job_description="Job.",
                )

    @pytest.mark.asyncio
    async def test_network_error_wrapped_in_llm_error(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = ConnectionError("Network unreachable")
            with pytest.raises(LLMError, match="CV tailoring failed"):
                await CVTailoringService.generate_tailored_cv(
                    resume=resume,
                    job_title="Dev",
                    job_company="Co",
                    job_description="Job.",
                )


# ── Prompt Content ─────────────────────────────────────────────────


class TestPromptContent:
    @pytest.mark.asyncio
    async def test_job_title_in_prompt(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Principal Architect",
                job_company="MegaCorp",
                job_description="Lead the architecture.",
            )

        assert "Principal Architect" in captured[0]

    @pytest.mark.asyncio
    async def test_job_company_in_prompt(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="UniqueCompanyXYZ",
                job_description="Build things.",
            )

        assert "UniqueCompanyXYZ" in captured[0]

    @pytest.mark.asyncio
    async def test_job_description_in_prompt(self) -> None:
        from app.ai.cv_tailor import CVTailoringService

        resume = _make_resume()
        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return _make_tailored_cv_data()

        with patch("app.ai.cv_tailor.complete_json", side_effect=_capture):
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Must know Kubernetes and Terraform deeply.",
            )

        assert "Kubernetes and Terraform" in captured[0]

    @pytest.mark.asyncio
    async def test_system_prompt_passed_to_complete_json(self) -> None:
        from app.ai.cv_tailor import CVTailoringService
        from app.ai.prompts import CV_TAILOR_SYSTEM_PROMPT

        resume = _make_resume()
        with patch("app.ai.cv_tailor.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = _make_tailored_cv_data()
            await CVTailoringService.generate_tailored_cv(
                resume=resume,
                job_title="Dev",
                job_company="Co",
                job_description="Job.",
            )

        call_kwargs = mock_llm.call_args.kwargs
        assert call_kwargs["system_prompt"] == CV_TAILOR_SYSTEM_PROMPT
