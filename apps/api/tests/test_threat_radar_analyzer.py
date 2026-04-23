"""
Unit tests for ThreatRadarAnalyzer and its helper functions.

Covers all four LLM methods (happy paths, LLMError fallbacks, edge cases)
plus the standalone helper functions.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from app.core.llm import LLMError

# ── Helpers ───────────────────────────────────────────────────────


def _make_occupation(
    soc_code: str = "15-1252.00",
    title: str = "Software Developer",
    automation_probability: float = 0.18,
    perception: float = 0.55,
    creative: float = 0.70,
    social: float = 0.80,
    category: str = "professional",
) -> dict:
    return {
        "soc_code": soc_code,
        "title": title,
        "automation_probability": automation_probability,
        "bottleneck_scores": {
            "perception_manipulation": perception,
            "creative_intelligence": creative,
            "social_intelligence": social,
        },
        "category": category,
    }


def _sanitize_passthrough(text: str, *, max_length: int, context: str):
    return text[:max_length], {}


# ── score_automation_risk ─────────────────────────────────────────


class TestScoreAutomationRisk:
    @pytest.mark.asyncio
    async def test_happy_path_returns_dict(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        occ = _make_occupation()
        llm_data: dict[str, Any] = {
            "contextual_risk_score": 25.0,
            "risk_level": "low",
            "vulnerable_tasks": ["data entry"],
            "resilient_tasks": ["system design"],
            "recommended_skills": ["AI/ML"],
            "analysis_reasoning": "Strong creative bottleneck.",
            "opportunity_inversions": [],
        }

        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=occ), \
             patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_data
            result = await ThreatRadarAnalyzer.score_automation_risk(
                soc_code="15-1252.00",
                skills_summary="Python, FastAPI, Docker",
                experience_summary="5 years backend engineering",
                years_experience=5.0,
            )

        assert result["contextual_risk_score"] == 25.0
        assert result["onet_soc_code"] == "15-1252.00"
        assert result["onet_occupation_title"] == "Software Developer"
        assert result["base_automation_probability"] == 0.18

    @pytest.mark.asyncio
    async def test_risk_score_clamped_above_100(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        occ = _make_occupation()
        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=occ), \
             patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"contextual_risk_score": 999}
            result = await ThreatRadarAnalyzer.score_automation_risk(
                soc_code="15-1252.00",
                skills_summary="Python",
                experience_summary="5 years",
                years_experience=5.0,
            )

        assert result["contextual_risk_score"] == 100.0

    @pytest.mark.asyncio
    async def test_risk_score_clamped_below_zero(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        occ = _make_occupation()
        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=occ), \
             patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"contextual_risk_score": -50}
            result = await ThreatRadarAnalyzer.score_automation_risk(
                soc_code="15-1252.00",
                skills_summary="Python",
                experience_summary="5 years",
                years_experience=5.0,
            )

        assert result["contextual_risk_score"] == 0.0

    @pytest.mark.asyncio
    async def test_llm_error_returns_fallback_dict(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        occ = _make_occupation(automation_probability=0.40)
        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=occ), \
             patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("rate limit")
            result = await ThreatRadarAnalyzer.score_automation_risk(
                soc_code="15-1252.00",
                skills_summary="Python",
                experience_summary="5 years",
                years_experience=5.0,
            )

        assert "contextual_risk_score" in result
        assert result["contextual_risk_score"] == 40.0  # 0.40 * 100
        assert "analysis_reasoning" in result

    @pytest.mark.asyncio
    async def test_unknown_soc_falls_back_to_title_search(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        fallback_occ = _make_occupation(soc_code="00-0000.00", title="General Professional")
        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=None), \
             patch("app.ai.threat_radar_analyzer.search_occupations_by_title", return_value=[fallback_occ]), \
             patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"contextual_risk_score": 30}
            result = await ThreatRadarAnalyzer.score_automation_risk(
                soc_code="99-9999.99",
                skills_summary="Python",
                experience_summary="5 years",
                years_experience=5.0,
            )

        assert result["onet_occupation_title"] == "General Professional"

    @pytest.mark.asyncio
    async def test_unknown_soc_no_title_match_uses_hardcoded_fallback(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=None), \
             patch("app.ai.threat_radar_analyzer.search_occupations_by_title", return_value=[]), \
             patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"contextual_risk_score": 30}
            result = await ThreatRadarAnalyzer.score_automation_risk(
                soc_code="99-9999.99",
                skills_summary="Python",
                experience_summary="5 years",
                years_experience=5.0,
            )

        assert result["onet_occupation_title"] == "General Professional"

    @pytest.mark.asyncio
    async def test_missing_score_uses_base_probability(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        occ = _make_occupation(automation_probability=0.50)
        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=occ), \
             patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {}  # no contextual_risk_score key
            result = await ThreatRadarAnalyzer.score_automation_risk(
                soc_code="15-1252.00",
                skills_summary="Python",
                experience_summary="5 years",
                years_experience=5.0,
            )

        assert result["contextual_risk_score"] == 50.0  # 0.50 * 100


# ── analyze_industry_trends ───────────────────────────────────────


class TestAnalyzeIndustryTrends:
    @pytest.mark.asyncio
    async def test_happy_path_returns_trend_dict(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        llm_data = {
            "trend_direction": "growing",
            "confidence": 0.75,
            "key_signals": ["AI adoption"],
            "impact_on_user": "Positive",
            "recommended_actions": ["Learn ML"],
            "data_sources": ["industry reports"],
        }
        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = llm_data
            result = await ThreatRadarAnalyzer.analyze_industry_trends(
                industry_name="Software Development",
                skills_summary="Python, ML",
                experience_summary="5 years backend",
            )

        assert result["trend_direction"] == "growing"
        assert result["industry_name"] == "Software Development"

    @pytest.mark.asyncio
    async def test_confidence_capped_at_0_85(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"confidence": 0.95, "trend_direction": "growing"}
            result = await ThreatRadarAnalyzer.analyze_industry_trends(
                industry_name="Tech",
                skills_summary="Python",
                experience_summary="5 years",
            )

        assert result["confidence"] == 0.85

    @pytest.mark.asyncio
    async def test_confidence_below_cap_not_modified(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"confidence": 0.60, "trend_direction": "stable"}
            result = await ThreatRadarAnalyzer.analyze_industry_trends(
                industry_name="Tech",
                skills_summary="Python",
                experience_summary="5 years",
            )

        assert result["confidence"] == 0.60

    @pytest.mark.asyncio
    async def test_empty_industry_returns_default(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        result = await ThreatRadarAnalyzer.analyze_industry_trends(
            industry_name="",
            skills_summary="Python",
            experience_summary="5 years",
        )

        assert result["trend_direction"] == "stable"
        assert result["industry_name"] == "Unknown"

    @pytest.mark.asyncio
    async def test_whitespace_only_industry_returns_default(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        result = await ThreatRadarAnalyzer.analyze_industry_trends(
            industry_name="   ",
            skills_summary="Python",
            experience_summary="5 years",
        )

        assert result["trend_direction"] == "stable"

    @pytest.mark.asyncio
    async def test_llm_error_returns_default_fallback(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("timeout")
            result = await ThreatRadarAnalyzer.analyze_industry_trends(
                industry_name="FinTech",
                skills_summary="Python",
                experience_summary="5 years",
            )

        assert result["trend_direction"] == "stable"
        assert result["industry_name"] == "FinTech"

    @pytest.mark.asyncio
    async def test_industry_name_injected_into_result(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"confidence": 0.5, "trend_direction": "declining"}
            result = await ThreatRadarAnalyzer.analyze_industry_trends(
                industry_name="Print Media",
                skills_summary="Writing",
                experience_summary="10 years",
            )

        assert result["industry_name"] == "Print Media"


# ── classify_skills_shield ────────────────────────────────────────


class TestClassifySkillsShield:
    @pytest.mark.asyncio
    async def test_happy_path_returns_classifications(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        occ = _make_occupation()
        classifications = [
            {"skill_name": "Python", "classification": "shield", "automation_resistance": 0.8},
            {"skill_name": "Data Entry", "classification": "exposure", "automation_resistance": 0.2},
        ]
        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=occ), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"classifications": classifications}
            result = await ThreatRadarAnalyzer.classify_skills_shield(
                skills_list=["Python", "Data Entry"],
                soc_code="15-1252.00",
            )

        assert len(result) == 2
        assert result[0]["skill_name"] == "Python"
        assert result[0]["classification"] == "shield"

    @pytest.mark.asyncio
    async def test_automation_resistance_clamped_above_1(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        occ = _make_occupation()
        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=occ), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "classifications": [
                    {"skill_name": "Python", "classification": "shield", "automation_resistance": 2.5}
                ]
            }
            result = await ThreatRadarAnalyzer.classify_skills_shield(
                skills_list=["Python"],
                soc_code="15-1252.00",
            )

        assert result[0]["automation_resistance"] == 1.0

    @pytest.mark.asyncio
    async def test_automation_resistance_clamped_below_0(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        occ = _make_occupation()
        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=occ), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "classifications": [
                    {"skill_name": "Excel", "classification": "exposure", "automation_resistance": -0.5}
                ]
            }
            result = await ThreatRadarAnalyzer.classify_skills_shield(
                skills_list=["Excel"],
                soc_code="15-1252.00",
            )

        assert result[0]["automation_resistance"] == 0.0

    @pytest.mark.asyncio
    async def test_empty_skills_list_returns_empty(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        result = await ThreatRadarAnalyzer.classify_skills_shield(
            skills_list=[],
            soc_code="15-1252.00",
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_unknown_soc_uses_fallback_occupation(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=None), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {
                "classifications": [
                    {"skill_name": "SQL", "classification": "neutral", "automation_resistance": 0.5}
                ]
            }
            result = await ThreatRadarAnalyzer.classify_skills_shield(
                skills_list=["SQL"],
                soc_code="99-9999.99",
            )

        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_llm_error_returns_default_classifications(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        occ = _make_occupation(perception=0.30, creative=0.30, social=0.30)  # avg=0.30 → exposure
        with patch("app.ai.threat_radar_analyzer.get_occupation_by_soc", return_value=occ), \
             patch("app.ai.threat_radar_analyzer.compute_bottleneck_average", return_value=0.30), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("timeout")
            result = await ThreatRadarAnalyzer.classify_skills_shield(
                skills_list=["Python", "Excel"],
                soc_code="15-1252.00",
            )

        assert len(result) == 2
        assert all(r["classification"] == "exposure" for r in result)


# ── generate_threat_assessment ────────────────────────────────────


class TestGenerateThreatAssessment:
    @pytest.mark.asyncio
    async def test_happy_path_returns_alerts(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        alerts = [
            {
                "category": "automation",
                "severity": "medium",
                "title": "Routine tasks at risk",
                "description": "Some of your tasks may be automated.",
                "opportunity": "Focus on leadership roles.",
                "evidence": {"sources": ["McKinsey 2024", "ONET data"]},
            }
        ]
        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"alerts": alerts}
            result = await ThreatRadarAnalyzer.generate_threat_assessment(
                risk_score=45.0,
                risk_level="medium",
                vulnerable_tasks=["data entry"],
                industry_trends_summary="Growing AI adoption",
                shield_skills=["Python"],
                exposure_skills=["Excel"],
                skills_summary="Python, Excel",
                experience_summary="5 years backend",
            )

        assert len(result) == 1
        assert result[0]["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_high_alert_downgraded_with_insufficient_evidence(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        alerts = [
            {
                "severity": "high",
                "title": "Job automation risk",
                "opportunity": "Learn new skills.",
                "evidence": {"sources": ["one_source"]},  # only 1 source
            }
        ]
        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"alerts": alerts}
            result = await ThreatRadarAnalyzer.generate_threat_assessment(
                risk_score=80.0,
                risk_level="high",
                vulnerable_tasks=[],
                industry_trends_summary="Declining",
                shield_skills=[],
                exposure_skills=["Excel"],
                skills_summary="Excel",
                experience_summary="2 years",
            )

        assert result[0]["severity"] == "medium"

    @pytest.mark.asyncio
    async def test_high_alert_kept_with_two_evidence_sources(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        alerts = [
            {
                "severity": "high",
                "title": "Job automation risk",
                "opportunity": "Pivot to management.",
                "evidence": {"sources": ["McKinsey 2024", "ONET data"]},
            }
        ]
        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"alerts": alerts}
            result = await ThreatRadarAnalyzer.generate_threat_assessment(
                risk_score=80.0,
                risk_level="high",
                vulnerable_tasks=[],
                industry_trends_summary="Declining",
                shield_skills=[],
                exposure_skills=["Excel"],
                skills_summary="Excel",
                experience_summary="2 years",
            )

        assert result[0]["severity"] == "high"

    @pytest.mark.asyncio
    async def test_empty_opportunity_gets_default_message(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        alerts = [
            {
                "severity": "low",
                "title": "Minor risk",
                "opportunity": "",  # empty
                "evidence": {"sources": []},
            }
        ]
        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"alerts": alerts}
            result = await ThreatRadarAnalyzer.generate_threat_assessment(
                risk_score=10.0,
                risk_level="low",
                vulnerable_tasks=[],
                industry_trends_summary="Stable",
                shield_skills=["Python"],
                exposure_skills=[],
                skills_summary="Python",
                experience_summary="5 years",
            )

        assert result[0]["opportunity"] != ""
        assert "adjacent roles" in result[0]["opportunity"]

    @pytest.mark.asyncio
    async def test_missing_opportunity_key_gets_default(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        alerts = [{"severity": "low", "title": "Risk", "evidence": {"sources": []}}]
        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.return_value = {"alerts": alerts}
            result = await ThreatRadarAnalyzer.generate_threat_assessment(
                risk_score=10.0,
                risk_level="low",
                vulnerable_tasks=[],
                industry_trends_summary="Stable",
                shield_skills=["Python"],
                exposure_skills=[],
                skills_summary="Python",
                experience_summary="5 years",
            )

        assert result[0]["opportunity"] != ""

    @pytest.mark.asyncio
    async def test_llm_error_returns_empty_list(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", new_callable=AsyncMock) as mock_llm:
            mock_llm.side_effect = LLMError("quota exceeded")
            result = await ThreatRadarAnalyzer.generate_threat_assessment(
                risk_score=50.0,
                risk_level="medium",
                vulnerable_tasks=["admin"],
                industry_trends_summary="Stable",
                shield_skills=["Python"],
                exposure_skills=["Excel"],
                skills_summary="Python, Excel",
                experience_summary="5 years",
            )

        assert result == []

    @pytest.mark.asyncio
    async def test_empty_vulnerable_tasks_formats_as_none(self) -> None:
        from app.ai.threat_radar_analyzer import ThreatRadarAnalyzer

        captured: list[str] = []

        async def _capture(**kwargs):
            captured.append(kwargs["prompt"])
            return {"alerts": []}

        with patch("app.ai.threat_radar_analyzer.sanitize_user_text", side_effect=_sanitize_passthrough), \
             patch("app.ai.threat_radar_analyzer.complete_json", side_effect=_capture):
            await ThreatRadarAnalyzer.generate_threat_assessment(
                risk_score=20.0,
                risk_level="low",
                vulnerable_tasks=[],
                industry_trends_summary="Stable",
                shield_skills=["Python"],
                exposure_skills=[],
                skills_summary="Python",
                experience_summary="5 years",
            )

        assert "None identified" in captured[0]


# ── Helper functions ──────────────────────────────────────────────


class TestFallbackOccupation:
    def test_returns_occupation_entry_with_given_soc(self) -> None:
        from app.ai.threat_radar_analyzer import _fallback_occupation

        result = _fallback_occupation("99-9999.99")
        assert result["soc_code"] == "99-9999.99"
        assert result["title"] == "General Professional"
        assert 0.0 <= result["automation_probability"] <= 1.0

    def test_bottleneck_scores_present(self) -> None:
        from app.ai.threat_radar_analyzer import _fallback_occupation

        result = _fallback_occupation("00-0000.00")
        assert "perception_manipulation" in result["bottleneck_scores"]
        assert "creative_intelligence" in result["bottleneck_scores"]
        assert "social_intelligence" in result["bottleneck_scores"]


class TestDefaultAutomationRisk:
    def test_returns_dict_with_expected_keys(self) -> None:
        from app.ai.threat_radar_analyzer import _default_automation_risk

        occ = _make_occupation(automation_probability=0.60)
        result = _default_automation_risk("15-1252.00", occ)
        assert result["contextual_risk_score"] == 60.0
        assert result["onet_soc_code"] == "15-1252.00"
        assert "analysis_reasoning" in result
        assert result["vulnerable_tasks"] == []

    def test_risk_level_computed_from_probability(self) -> None:
        from app.ai.threat_radar_analyzer import _default_automation_risk

        occ = _make_occupation(automation_probability=0.80)
        result = _default_automation_risk("15-1252.00", occ)
        assert result["risk_level"] == "high"


class TestDefaultIndustryTrend:
    def test_returns_stable_direction(self) -> None:
        from app.ai.threat_radar_analyzer import _default_industry_trend

        result = _default_industry_trend("FinTech")
        assert result["trend_direction"] == "stable"
        assert result["confidence"] == 0.3
        assert result["industry_name"] == "FinTech"

    def test_empty_key_signals(self) -> None:
        from app.ai.threat_radar_analyzer import _default_industry_trend

        result = _default_industry_trend("Tech")
        assert result["key_signals"] == []


class TestDefaultShieldClassifications:
    def test_high_bottleneck_average_maps_to_shield(self) -> None:
        from app.ai.threat_radar_analyzer import _default_shield_classifications

        occ = _make_occupation(perception=0.80, creative=0.80, social=0.80)
        with patch("app.ai.threat_radar_analyzer.compute_bottleneck_average", return_value=0.80):
            result = _default_shield_classifications(["Python", "SQL"], occ)

        assert all(r["classification"] == "shield" for r in result)

    def test_low_bottleneck_average_maps_to_exposure(self) -> None:
        from app.ai.threat_radar_analyzer import _default_shield_classifications

        occ = _make_occupation(perception=0.20, creative=0.20, social=0.20)
        with patch("app.ai.threat_radar_analyzer.compute_bottleneck_average", return_value=0.20):
            result = _default_shield_classifications(["Data Entry"], occ)

        assert result[0]["classification"] == "exposure"

    def test_mid_bottleneck_maps_to_neutral(self) -> None:
        from app.ai.threat_radar_analyzer import _default_shield_classifications

        occ = _make_occupation(perception=0.50, creative=0.50, social=0.50)
        with patch("app.ai.threat_radar_analyzer.compute_bottleneck_average", return_value=0.50):
            result = _default_shield_classifications(["Writing"], occ)

        assert result[0]["classification"] == "neutral"

    def test_one_entry_per_skill(self) -> None:
        from app.ai.threat_radar_analyzer import _default_shield_classifications

        occ = _make_occupation()
        with patch("app.ai.threat_radar_analyzer.compute_bottleneck_average", return_value=0.50):
            result = _default_shield_classifications(["A", "B", "C"], occ)

        assert len(result) == 3
        assert [r["skill_name"] for r in result] == ["A", "B", "C"]


class TestProbabilityToRiskLevel:
    def test_high_probability_is_high(self) -> None:
        from app.ai.threat_radar_analyzer import _probability_to_risk_level

        assert _probability_to_risk_level(0.70) == "high"
        assert _probability_to_risk_level(0.99) == "high"

    def test_medium_probability_is_medium(self) -> None:
        from app.ai.threat_radar_analyzer import _probability_to_risk_level

        assert _probability_to_risk_level(0.30) == "medium"
        assert _probability_to_risk_level(0.60) == "medium"

    def test_low_probability_is_low(self) -> None:
        from app.ai.threat_radar_analyzer import _probability_to_risk_level

        assert _probability_to_risk_level(0.10) == "low"
        assert _probability_to_risk_level(0.0) == "low"

    def test_boundary_at_0_70_is_high(self) -> None:
        from app.ai.threat_radar_analyzer import _probability_to_risk_level

        assert _probability_to_risk_level(0.70) == "high"

    def test_boundary_at_0_30_is_medium(self) -> None:
        from app.ai.threat_radar_analyzer import _probability_to_risk_level

        assert _probability_to_risk_level(0.30) == "medium"
