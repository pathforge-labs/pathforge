"""
PathForge — Hidden Job Market Detector™ Models
================================================
Domain models for the Hidden Job Market Detector — the industry's
first system that monitors company growth signals, matches them to
Career DNA, and surfaces pre-listing opportunities with proactive
outreach templates.

Models:
    CompanySignal              — Hub entity: one detected company growth signal
    SignalMatchResult          — Career DNA ↔ signal match analysis
    OutreachTemplate           — AI-generated proactive outreach message
    HiddenOpportunity          — Surfaced pre-listing opportunity
    HiddenJobMarketPreference  — User monitoring preferences

Enums:
    SignalType         — funding | office_expansion | key_hire | tech_stack_change | competitor_layoff | revenue_growth
    SignalStatus       — detected | matched | actioned | expired | dismissed
    OutreachTemplateType — introduction | referral_request | informational_interview | direct_application
    OutreachTone       — professional | casual | enthusiastic

Proprietary Innovations:
    🔥 Company Signal Radar™      — Multi-source growth signal detection
    🔥 Opportunity Surfacer™      — Pre-listing opportunity prediction
    🔥 Smart Outreach Engine™     — Career DNA–personalized outreach
"""

from __future__ import annotations

import enum
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.career_dna import CareerDNA
    from app.models.user import User


# ── Enums ──────────────────────────────────────────────────────


class SignalType(enum.StrEnum):
    """Classification for company growth signal types."""

    FUNDING = "funding"
    OFFICE_EXPANSION = "office_expansion"
    KEY_HIRE = "key_hire"
    TECH_STACK_CHANGE = "tech_stack_change"
    COMPETITOR_LAYOFF = "competitor_layoff"
    REVENUE_GROWTH = "revenue_growth"


class SignalStatus(enum.StrEnum):
    """Lifecycle status of a company signal."""

    DETECTED = "detected"
    MATCHED = "matched"
    ACTIONED = "actioned"
    EXPIRED = "expired"
    DISMISSED = "dismissed"


class OutreachTemplateType(enum.StrEnum):
    """Classification for outreach template types."""

    INTRODUCTION = "introduction"
    REFERRAL_REQUEST = "referral_request"
    INFORMATIONAL_INTERVIEW = "informational_interview"
    DIRECT_APPLICATION = "direct_application"


class OutreachTone(enum.StrEnum):
    """Tone setting for outreach messages."""

    PROFESSIONAL = "professional"
    CASUAL = "casual"
    ENTHUSIASTIC = "enthusiastic"


# ── CompanySignal ──────────────────────────────────────────────


class CompanySignal(Base, UUIDMixin, TimestampMixin):
    """Hidden Job Market Detector™ — hub entity for one company signal.

    One record per detected growth signal for a specific company.
    Each signal is matched against Career DNA to assess relevance,
    and can trigger:
        - Outreach template generation
        - Hidden opportunity surfacing
        - Proactive alerts

    Confidence is hard-capped at 0.85 (MAX_SIGNAL_CONFIDENCE).
    All responses include data_source + disclaimer transparency.
    """

    __tablename__ = "company_signals"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_company_signal_confidence_cap",
        ),
    )

    # ── Foreign keys ──
    career_dna_id: Mapped[str] = mapped_column(
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Core fields ──
    company_name: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    signal_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(
        String(500), nullable=False,
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    strength: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
    )
    source: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    source_url: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=SignalStatus.DETECTED.value,
        server_default="detected", nullable=False, index=True,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )

    # ── Temporal fields ──
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        server_default="now()",
        nullable=False,
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-generated signal intelligence based on public company data",
        server_default="AI-generated signal intelligence based on public company data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "This signal analysis is AI-generated intelligence based on public data, "
            "not a guarantee of hiring intent. Company plans may change. "
            "Maximum confidence: 85%."
        ),
        server_default=(
            "This signal analysis is AI-generated intelligence based on public data, "
            "not a guarantee of hiring intent. Company plans may change. "
            "Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="company_signals",
    )
    user: Mapped[User] = relationship("User")
    match_results: Mapped[list[SignalMatchResult]] = relationship(
        "SignalMatchResult",
        back_populates="signal",
        cascade="all, delete-orphan",
    )
    outreach_templates: Mapped[list[OutreachTemplate]] = relationship(
        "OutreachTemplate",
        back_populates="signal",
        cascade="all, delete-orphan",
    )
    hidden_opportunities: Mapped[list[HiddenOpportunity]] = relationship(
        "HiddenOpportunity",
        back_populates="signal",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<CompanySignal(id={self.id}, company={self.company_name}, "
            f"type={self.signal_type}, strength={self.strength})>"
        )


# ── SignalMatchResult ──────────────────────────────────────────


class SignalMatchResult(Base, UUIDMixin, TimestampMixin):
    """Career DNA ↔ signal match analysis.

    Stores the result of matching a company growth signal
    against the user's Career DNA profile, including:
        - Overall match score (0.0 - 1.0)
        - Skill overlap analysis
        - Role relevance assessment
        - Matched skills breakdown (JSON)
    """

    __tablename__ = "signal_match_results"

    signal_id: Mapped[str] = mapped_column(
        ForeignKey("company_signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    skill_overlap: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    role_relevance: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    explanation: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    matched_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    relevance_reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Relationships ──
    signal: Mapped[CompanySignal] = relationship(
        "CompanySignal", back_populates="match_results",
    )

    def __repr__(self) -> str:
        return (
            f"<SignalMatchResult(signal_id={self.signal_id}, "
            f"match_score={self.match_score})>"
        )


# ── OutreachTemplate ───────────────────────────────────────────


class OutreachTemplate(Base, UUIDMixin, TimestampMixin):
    """AI-generated proactive outreach message.

    Smart Outreach Engine™ — generates personalized outreach
    templates by combining the detected company signal with
    the user's Career DNA profile. Templates cite specific
    signals and relevant experience, not generic introductions.
    """

    __tablename__ = "outreach_templates"

    signal_id: Mapped[str] = mapped_column(
        ForeignKey("company_signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    template_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )
    tone: Mapped[str] = mapped_column(
        String(20),
        default=OutreachTone.PROFESSIONAL.value,
        server_default="professional",
        nullable=False,
    )
    subject_line: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    body: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    personalization_points: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
    )

    # ── Relationships ──
    signal: Mapped[CompanySignal] = relationship(
        "CompanySignal", back_populates="outreach_templates",
    )

    def __repr__(self) -> str:
        return (
            f"<OutreachTemplate(type={self.template_type}, "
            f"tone={self.tone})>"
        )


# ── HiddenOpportunity ─────────────────────────────────────────


class HiddenOpportunity(Base, UUIDMixin, TimestampMixin):
    """Surfaced pre-listing opportunity from signal analysis.

    Opportunity Surfacer™ — predicts likely job openings based
    on detected company growth signals. Each opportunity includes
    predicted role, seniority, timeline, and probability score.
    """

    __tablename__ = "hidden_opportunities"

    signal_id: Mapped[str] = mapped_column(
        ForeignKey("company_signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    predicted_role: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    predicted_seniority: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    predicted_timeline_days: Mapped[int | None] = mapped_column(
        Integer, nullable=True,
    )
    probability: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    reasoning: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    required_skills: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    salary_range_min: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    salary_range_max: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )
    currency: Mapped[str] = mapped_column(
        String(10), default="EUR", server_default="EUR", nullable=False,
    )

    # ── Relationships ──
    signal: Mapped[CompanySignal] = relationship(
        "CompanySignal", back_populates="hidden_opportunities",
    )

    def __repr__(self) -> str:
        return (
            f"<HiddenOpportunity(role={self.predicted_role}, "
            f"probability={self.probability})>"
        )


# ── HiddenJobMarketPreference ─────────────────────────────────


class HiddenJobMarketPreference(Base, UUIDMixin, TimestampMixin):
    """User preferences for Hidden Job Market Detector™.

    Supports user autonomy (PathForge Manifesto #5):
    users control signal monitoring sensitivity, enabled signal
    types, outreach limits, and notification preferences.
    """

    __tablename__ = "hidden_job_market_preferences"

    # ── Foreign keys ──
    career_dna_id: Mapped[str] = mapped_column(
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── Preference fields ──
    min_signal_strength: Mapped[float] = mapped_column(
        Float, default=0.3, server_default="0.3", nullable=False,
    )
    enabled_signal_types: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    max_outreach_per_week: Mapped[int] = mapped_column(
        Integer, default=10, server_default="10", nullable=False,
    )
    auto_generate_outreach: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false", nullable=False,
    )
    notification_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="hidden_job_market_preference",
    )

    def __repr__(self) -> str:
        return (
            f"<HiddenJobMarketPreference(user_id={self.user_id}, "
            f"min_strength={self.min_signal_strength})>"
        )
