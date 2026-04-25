"""
PathForge — Hidden Job Market Detector™ AI Analyzer
=====================================================
LLM-powered signal analysis pipeline for detecting company growth
signals, matching them to Career DNA, generating outreach templates,
and surfacing hidden opportunities.

Methods:
    analyze_company_signals  — Detect growth signals for a company
    match_signal_to_career_dna — Match signal to user profile
    generate_outreach         — Create personalized outreach template
    surface_opportunities     — Predict hidden opportunities

Static Helpers:
    compute_signal_confidence    — Composite confidence, capped at 0.85
    calculate_match_strength     — Career DNA ↔ signal alignment
    validate_signal_data         — Structural validation
    calculate_opportunity_probability — Probability scoring

Prompt version: 1.0.0
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any

from app.ai.hidden_job_market_prompts import (
    COMPANY_SIGNAL_ANALYSIS_PROMPT,
    OPPORTUNITY_SURFACING_PROMPT,
    OUTREACH_GENERATION_PROMPT,
    SIGNAL_MATCH_PROMPT,
)
from app.core.llm import LLMError, LLMTier, complete_json
from app.core.prompt_sanitizer import sanitize_user_text

logger = logging.getLogger(__name__)

MAX_SIGNAL_CONFIDENCE = 0.85

VALID_SIGNAL_TYPES = frozenset({
    "funding",
    "office_expansion",
    "key_hire",
    "tech_stack_change",
    "competitor_layoff",
    "revenue_growth",
})

VALID_OUTREACH_TYPES = frozenset({
    "introduction",
    "referral_request",
    "informational_interview",
    "direct_application",
})

VALID_OUTREACH_TONES = frozenset({
    "professional",
    "casual",
    "enthusiastic",
})


class HiddenJobMarketAnalyzer:
    """AI pipeline for Hidden Job Market signal detection and matching."""

    # ── LLM Methods ────────────────────────────────────────────

    @staticmethod
    async def analyze_company_signals(
        *,
        company_name: str,
        industry: str,
        current_role: str,
        current_seniority: str,
    ) -> dict[str, Any]:
        """Detect growth and hiring signals for a specific company.

        Uses the Company Signal Radar™ prompt to analyze a company
        for 6 signal types and return structured signal data.

        Args:
            company_name: Target company to analyze.
            industry: Industry context for better detection.
            current_role: User's current role title.
            current_seniority: User's seniority level.

        Returns:
            Dict with signals list and company summary.
        """
        clean_company, _ = sanitize_user_text(
            company_name, max_length=255, context="signal_company",
        )
        clean_industry, _ = sanitize_user_text(
            industry or "Technology", max_length=255, context="signal_industry",
        )
        clean_role, _ = sanitize_user_text(
            current_role or "Software Engineer", max_length=255,
            context="signal_role",
        )
        clean_seniority, _ = sanitize_user_text(
            current_seniority or "mid", max_length=100,
            context="signal_seniority",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=COMPANY_SIGNAL_ANALYSIS_PROMPT.format(
                    company_name=clean_company,
                    industry=clean_industry,
                    current_role=clean_role,
                    current_seniority=clean_seniority,
                ),
                system_prompt="You are the PathForge Hidden Job Market Detector.",
                tier=LLMTier.PRIMARY,
                temperature=0.5,
                max_tokens=1024,
            )

            _clamp_signal_analysis(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Signal analysis for %s completed — "
                "%d signals detected (%.2fs)",
                clean_company,
                len(result.get("signals", [])),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Signal analysis failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {"signals": [], "company_summary": "Analysis unavailable."}

    @staticmethod
    async def match_signal_to_career_dna(
        *,
        company_name: str,
        signal_type: str,
        signal_title: str,
        signal_description: str,
        signal_strength: float,
        primary_role: str,
        seniority_level: str,
        primary_industry: str,
        skills: str,
        years_experience: int,
    ) -> dict[str, Any]:
        """Match a detected signal against the user's Career DNA.

        Args:
            company_name: Company that generated the signal.
            signal_type: Type of signal detected.
            signal_title: Signal headline.
            signal_description: Signal analysis text.
            signal_strength: Signal strength (0-1).
            primary_role: User's primary role from Career DNA.
            seniority_level: User's seniority level.
            primary_industry: User's industry.
            skills: Comma-separated skills string.
            years_experience: Total years of experience.

        Returns:
            Dict with match_score, skill_overlap, role_relevance, etc.
        """
        clean_title, _ = sanitize_user_text(
            signal_title, max_length=255, context="match_title",
        )
        clean_desc, _ = sanitize_user_text(
            signal_description or "", max_length=2000, context="match_desc",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer", max_length=255,
            context="match_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "general", max_length=3000, context="match_skills",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=SIGNAL_MATCH_PROMPT.format(
                    company_name=company_name,
                    signal_type=signal_type,
                    signal_title=clean_title,
                    signal_description=clean_desc,
                    signal_strength=signal_strength,
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    primary_industry=primary_industry or "Technology",
                    skills=clean_skills,
                    years_experience=years_experience,
                ),
                system_prompt="You are the PathForge Hidden Job Market Detector.",
                tier=LLMTier.PRIMARY,
                temperature=0.4,
                max_tokens=512,
            )

            _clamp_match_result(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Signal match completed — match_score=%.2f (%.2fs)",
                result.get("match_score", 0.0), elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Signal match failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {}

    @staticmethod
    async def generate_outreach(
        *,
        company_name: str,
        signal_type: str,
        signal_title: str,
        signal_description: str,
        primary_role: str,
        skills: str,
        years_experience: int,
        primary_industry: str,
        template_type: str = "introduction",
        tone: str = "professional",
        custom_notes: str | None = None,
    ) -> dict[str, Any]:
        """Generate a personalized outreach template.

        Args:
            company_name: Target company.
            signal_type: Signal type that prompted outreach.
            signal_title: Signal headline.
            signal_description: Signal analysis text.
            primary_role: User's primary role.
            skills: User's key skills.
            years_experience: Years of experience.
            primary_industry: User's industry.
            template_type: Outreach template type.
            tone: Message tone.
            custom_notes: Optional personalization notes.

        Returns:
            Dict with subject_line, body, personalization_points, confidence.
        """
        clean_title, _ = sanitize_user_text(
            signal_title, max_length=255, context="outreach_title",
        )
        clean_desc, _ = sanitize_user_text(
            signal_description or "", max_length=2000,
            context="outreach_desc",
        )
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer", max_length=255,
            context="outreach_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "general", max_length=3000, context="outreach_skills",
        )
        clean_notes, _ = sanitize_user_text(
            custom_notes or "None provided", max_length=1000,
            context="outreach_notes",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=OUTREACH_GENERATION_PROMPT.format(
                    company_name=company_name,
                    signal_type=signal_type,
                    signal_title=clean_title,
                    signal_description=clean_desc,
                    primary_role=clean_role,
                    skills=clean_skills,
                    years_experience=years_experience,
                    primary_industry=primary_industry or "Technology",
                    template_type=template_type,
                    tone=tone,
                    custom_notes=clean_notes,
                ),
                system_prompt="You are the PathForge Hidden Job Market Detector.",
                tier=LLMTier.PRIMARY,
                temperature=0.6,
                max_tokens=768,
            )

            _clamp_outreach(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Outreach generation completed (%.2fs)", elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Outreach generation failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {}

    @staticmethod
    async def surface_opportunities(
        *,
        signals: list[dict[str, Any]],
        primary_role: str,
        seniority_level: str,
        skills: str,
        primary_industry: str,
    ) -> dict[str, Any]:
        """Predict hidden opportunities from signal clusters.

        Args:
            signals: List of detected signal dicts.
            primary_role: User's primary role.
            seniority_level: User's seniority level.
            skills: User's key skills.
            primary_industry: User's industry.

        Returns:
            Dict with opportunities list.
        """
        clean_role, _ = sanitize_user_text(
            primary_role or "Software Engineer", max_length=255,
            context="opportunity_role",
        )
        clean_skills, _ = sanitize_user_text(
            skills or "general", max_length=3000,
            context="opportunity_skills",
        )

        start = time.monotonic()
        try:
            result: dict[str, Any] = await complete_json(
                prompt=OPPORTUNITY_SURFACING_PROMPT.format(
                    signals_json=json.dumps(signals, indent=2, default=str),
                    primary_role=clean_role,
                    seniority_level=seniority_level or "mid",
                    skills=clean_skills,
                    primary_industry=primary_industry or "Technology",
                ),
                system_prompt="You are the PathForge Hidden Job Market Detector.",
                tier=LLMTier.PRIMARY,
                temperature=0.5,
                max_tokens=1024,
            )

            _clamp_opportunities(result)

            elapsed = time.monotonic() - start
            logger.info(
                "Opportunity surfacing completed — "
                "%d opportunities (%.2fs)",
                len(result.get("opportunities", [])),
                elapsed,
            )
            return result

        except LLMError as exc:
            elapsed = time.monotonic() - start
            logger.error(
                "Opportunity surfacing failed (%.2fs): %s",
                elapsed, str(exc)[:200],
            )
            return {"opportunities": []}

    # ── Static Helpers ─────────────────────────────────────────

    @staticmethod
    def compute_signal_confidence(
        *,
        llm_confidence: float,
        signal_strength: float = 0.5,
        career_dna_completeness: float = 0.5,
    ) -> float:
        """Compute composite signal confidence, capped at 0.85.

        Formula:
            weighted = 0.40 × llm_confidence
                     + 0.35 × signal_strength
                     + 0.25 × career_dna_completeness
            clamped to [0.0, MAX_SIGNAL_CONFIDENCE]

        Args:
            llm_confidence: Raw LLM confidence (0-1).
            signal_strength: Signal strength factor (0-1).
            career_dna_completeness: Career DNA completeness (0-1).

        Returns:
            Capped confidence from 0.0 to 0.85.
        """
        llm_factor = max(0.0, min(MAX_SIGNAL_CONFIDENCE, llm_confidence))
        strength_factor = max(0.0, min(1.0, signal_strength))
        dna_factor = max(0.0, min(1.0, career_dna_completeness))

        weighted = (
            0.40 * llm_factor
            + 0.35 * strength_factor
            + 0.25 * dna_factor
        )

        return float(
            max(0.0, min(MAX_SIGNAL_CONFIDENCE, round(weighted, 3)))
        )

    @staticmethod
    def calculate_match_strength(
        *,
        skill_overlap: float,
        role_relevance: float,
        signal_strength: float = 0.5,
    ) -> float:
        """Calculate Career DNA ↔ signal match strength.

        Combines skill overlap, role relevance, and signal strength.

        Args:
            skill_overlap: Skill overlap ratio (0-1).
            role_relevance: Role relevance ratio (0-1).
            signal_strength: Signal strength (0-1).

        Returns:
            Match strength from 0.0 to 1.0.
        """
        skill_factor = max(0.0, min(1.0, skill_overlap))
        role_factor = max(0.0, min(1.0, role_relevance))
        strength = max(0.0, min(1.0, signal_strength))

        combined = (
            0.45 * skill_factor
            + 0.35 * role_factor
            + 0.20 * strength
        )
        return float(max(0.0, min(1.0, round(combined, 3))))

    @staticmethod
    def validate_signal_data(data: dict[str, Any]) -> tuple[bool, str]:
        """Validate structural completeness of signal data.

        Args:
            data: Signal data dictionary to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        required_fields = [
            "signal_type", "title", "strength", "confidence",
        ]
        for field in required_fields:
            if not data.get(field) and data.get(field) != 0:
                return False, f"Missing required field: {field}"

        if data.get("signal_type") not in VALID_SIGNAL_TYPES:
            return False, f"Invalid signal_type: {data.get('signal_type')}"

        return True, ""

    @staticmethod
    def calculate_opportunity_probability(
        *,
        signal_count: int,
        avg_signal_strength: float,
        match_score: float = 0.5,
    ) -> float:
        """Calculate probability for a predicted opportunity.

        Args:
            signal_count: Number of supporting signals.
            avg_signal_strength: Average strength of supporting signals.
            match_score: Career DNA match score.

        Returns:
            Probability from 0.0 to 0.85.
        """
        count_factor = min(1.0, signal_count / 5.0)
        strength = max(0.0, min(1.0, avg_signal_strength))
        match = max(0.0, min(1.0, match_score))

        combined = (
            0.35 * count_factor
            + 0.40 * strength
            + 0.25 * match
        )
        return float(
            max(0.0, min(MAX_SIGNAL_CONFIDENCE, round(combined, 3)))
        )


# ── Clamping Validators (module-level, testable) ──────────────


def _clamp_signal_analysis(data: dict[str, Any]) -> None:
    """Validate and clamp signal analysis fields in-place."""
    signals = data.get("signals", [])
    if not isinstance(signals, list):
        data["signals"] = []
    else:
        for signal in signals:
            # Validate signal type
            if signal.get("signal_type", "") not in VALID_SIGNAL_TYPES:
                signal["signal_type"] = "funding"
            # Cap confidence
            conf = signal.get("confidence", 0.5)
            signal["confidence"] = max(
                0.0, min(MAX_SIGNAL_CONFIDENCE, float(conf))
            )
            # Cap strength
            strength = signal.get("strength", 0.5)
            signal["strength"] = max(0.0, min(1.0, float(strength)))
            # Ensure title
            if not signal.get("title"):
                signal["title"] = "Untitled signal"
            # Ensure description
            if not signal.get("description"):
                signal["description"] = "No details available."

    # Ensure company_summary
    if not data.get("company_summary"):
        data["company_summary"] = "No summary available."


def _clamp_match_result(data: dict[str, Any]) -> None:
    """Validate and clamp match result fields in-place."""
    data["match_score"] = max(
        0.0, min(1.0, float(data.get("match_score", 0.0)))
    )
    data["skill_overlap"] = max(
        0.0, min(1.0, float(data.get("skill_overlap", 0.0)))
    )
    data["role_relevance"] = max(
        0.0, min(1.0, float(data.get("role_relevance", 0.0)))
    )

    if not data.get("explanation"):
        data["explanation"] = "No match explanation available."

    matched = data.get("matched_skills")
    if not isinstance(matched, dict):
        data["matched_skills"] = {
            "highly_relevant": [],
            "partially_relevant": [],
            "missing_but_learnable": [],
        }


def _clamp_outreach(data: dict[str, Any]) -> None:
    """Validate and clamp outreach template fields in-place."""
    if not data.get("subject_line"):
        data["subject_line"] = "Connection opportunity"
    if not data.get("body"):
        data["body"] = "Unable to generate outreach content."

    conf = data.get("confidence", 0.5)
    data["confidence"] = max(
        0.0, min(MAX_SIGNAL_CONFIDENCE, float(conf))
    )

    points = data.get("personalization_points")
    if not isinstance(points, dict):
        data["personalization_points"] = {
            "signal_reference": "",
            "skill_highlight": "",
            "value_proposition": "",
        }


def _clamp_opportunities(data: dict[str, Any]) -> None:
    """Validate and clamp opportunity surfacing results in-place."""
    opportunities = data.get("opportunities", [])
    if not isinstance(opportunities, list):
        data["opportunities"] = []
    else:
        for opp in opportunities:
            # Ensure role
            if not opp.get("predicted_role"):
                opp["predicted_role"] = "Unknown role"
            # Cap probability
            prob = opp.get("probability", 0.0)
            opp["probability"] = max(
                0.0, min(MAX_SIGNAL_CONFIDENCE, float(prob))
            )
            # Ensure reasoning
            if not opp.get("reasoning"):
                opp["reasoning"] = "No reasoning provided."
            # Validate skills
            skills = opp.get("required_skills")
            if not isinstance(skills, dict):
                opp["required_skills"] = {
                    "must_have": [],
                    "nice_to_have": [],
                }
