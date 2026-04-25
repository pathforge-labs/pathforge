"""
PathForge — Interview Intelligence™ Models
=============================================
Domain models for the Interview Intelligence Engine — the industry's
first integrated system combining company-specific preparation,
Career DNA–powered STAR examples, and data-backed salary negotiation.

Models:
    InterviewPrep         — Hub entity for one company+role prep session
    CompanyInsight        — Company intelligence layer (format, culture, salary)
    InterviewQuestion     — Predicted questions with AI-generated answers
    STARExample           — Career DNA–mapped STAR responses
    InterviewPreference   — User autonomy preferences

Enums:
    PrepStatus       — draft | analyzing | completed | failed
    InsightType      — format | culture | salary_band | process | values
    QuestionCategory — behavioral | technical | situational | culture_fit | salary
    PrepDepth        — quick | standard | comprehensive

Proprietary Innovations:
    🔥 Career DNA Interview Mapper™   — STAR examples from YOUR experience
    🔥 Negotiation Script Engine™     — Data-backed salary scripts
    🔥 Company Culture Decoder™       — Culture-to-DNA alignment scoring
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


class PrepStatus(enum.StrEnum):
    """Lifecycle status of an interview preparation session."""

    DRAFT = "draft"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"


class InsightType(enum.StrEnum):
    """Classification for company insight categories."""

    FORMAT = "format"
    CULTURE = "culture"
    SALARY_BAND = "salary_band"
    PROCESS = "process"
    VALUES = "values"


class QuestionCategory(enum.StrEnum):
    """Classification for interview question types."""

    BEHAVIORAL = "behavioral"
    TECHNICAL = "technical"
    SITUATIONAL = "situational"
    CULTURE_FIT = "culture_fit"
    SALARY = "salary"


class PrepDepth(enum.StrEnum):
    """Preparation depth preference."""

    QUICK = "quick"
    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"


# ── InterviewPrep ──────────────────────────────────────────────


class InterviewPrep(Base, UUIDMixin, TimestampMixin):
    """Interview Intelligence™ — hub entity for one prep session.

    One record per company+role preparation. Each prep session
    combines Career DNA context with LLM-powered company analysis
    to provide:
        - Company-specific interview questions
        - Personalized STAR examples from Career DNA
        - Data-backed salary negotiation scripts

    Confidence is hard-capped at 0.85 (MAX_INTERVIEW_CONFIDENCE).
    All responses include data_source + disclaimer transparency.
    """

    __tablename__ = "interview_preps"
    __table_args__ = (
        CheckConstraint(
            "confidence_score <= 0.85",
            name="ck_interview_prep_confidence_cap",
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
    target_role: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(20), default=PrepStatus.COMPLETED.value,
        server_default="completed", nullable=False, index=True,
    )
    prep_depth: Mapped[str] = mapped_column(
        String(20), default=PrepDepth.STANDARD.value,
        server_default="standard", nullable=False,
    )

    # ── Intelligence scores ──
    confidence_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    culture_alignment_score: Mapped[float | None] = mapped_column(
        Float, nullable=True,
    )

    # ── Company brief ──
    interview_format: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    company_brief: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )

    # ── Transparency (PathForge Manifesto) ──
    data_source: Mapped[str] = mapped_column(
        String(200),
        default="AI-generated interview intelligence based on Career DNA and market data",
        server_default="AI-generated interview intelligence based on Career DNA and market data",
        nullable=False,
    )
    disclaimer: Mapped[str] = mapped_column(
        String(500),
        default=(
            "This interview preparation is AI-generated intelligence, not a guarantee. "
            "Actual interview questions and company culture may differ from predictions. "
            "Maximum confidence: 85%."
        ),
        server_default=(
            "This interview preparation is AI-generated intelligence, not a guarantee. "
            "Actual interview questions and company culture may differ from predictions. "
            "Maximum confidence: 85%."
        ),
        nullable=False,
    )

    # ── Computed timestamp ──
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(tz=UTC),
        server_default="now()",
        nullable=False,
    )

    # ── Relationships ──
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="interview_preps",
    )
    user: Mapped[User] = relationship("User")
    insights: Mapped[list[CompanyInsight]] = relationship(
        "CompanyInsight",
        back_populates="interview_prep",
        cascade="all, delete-orphan",
    )
    questions: Mapped[list[InterviewQuestion]] = relationship(
        "InterviewQuestion",
        back_populates="interview_prep",
        cascade="all, delete-orphan",
    )
    star_examples: Mapped[list[STARExample]] = relationship(
        "STARExample",
        back_populates="interview_prep",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<InterviewPrep(id={self.id}, company={self.company_name}, "
            f"role={self.target_role}, confidence={self.confidence_score})>"
        )


# ── CompanyInsight ─────────────────────────────────────────────


class CompanyInsight(Base, UUIDMixin, TimestampMixin):
    """Company intelligence layer.

    Stores structured insights extracted via LLM analysis:
        - Interview format (rounds, panel vs 1:1, coding tests)
        - Culture signals (work style, values, team dynamics)
        - Salary bands (from Salary Intelligence Engine™ data)
        - Process details (typical timeline, decision flow)
        - Company values (mission, stated priorities)
    """

    __tablename__ = "company_insights"

    interview_prep_id: Mapped[str] = mapped_column(
        ForeignKey("interview_preps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insight_type: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )
    title: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    content: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
    )
    summary: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    source: Mapped[str | None] = mapped_column(
        String(200), nullable=True,
    )
    confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
    )

    # ── Relationships ──
    interview_prep: Mapped[InterviewPrep] = relationship(
        "InterviewPrep", back_populates="insights",
    )

    def __repr__(self) -> str:
        return (
            f"<CompanyInsight(type={self.insight_type}, "
            f"title={self.title})>"
        )


# ── InterviewQuestion ──────────────────────────────────────────


class InterviewQuestion(Base, UUIDMixin, TimestampMixin):
    """Predicted interview question with AI-generated answer.

    Company+role-specific questions categorized by type.
    Each question includes a suggested answer strategy and
    frequency weight (how likely to be asked).
    """

    __tablename__ = "interview_questions"

    interview_prep_id: Mapped[str] = mapped_column(
        ForeignKey("interview_preps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True,
    )
    question_text: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    suggested_answer: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    answer_strategy: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    frequency_weight: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
    )
    difficulty_level: Mapped[str | None] = mapped_column(
        String(20), nullable=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False,
    )

    # ── Relationships ──
    interview_prep: Mapped[InterviewPrep] = relationship(
        "InterviewPrep", back_populates="questions",
    )
    star_examples: Mapped[list[STARExample]] = relationship(
        "STARExample",
        back_populates="question",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<InterviewQuestion(category={self.category}, "
            f"order={self.order_index})>"
        )


# ── STARExample ────────────────────────────────────────────────


class STARExample(Base, UUIDMixin, TimestampMixin):
    """Career DNA–mapped STAR response.

    Career DNA Interview Mapper™ — generates personalized STAR
    (Situation, Task, Action, Result) examples by mapping the
    user's actual experience from Career DNA dimensions to
    likely interview questions.

    Unlike generic STAR templates, these are YOUR stories.
    """

    __tablename__ = "star_examples"

    interview_prep_id: Mapped[str] = mapped_column(
        ForeignKey("interview_preps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[str | None] = mapped_column(
        ForeignKey("interview_questions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ── STAR components ──
    situation: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    task: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    action: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    result: Mapped[str] = mapped_column(
        Text, nullable=False,
    )

    # ── Career DNA mapping ──
    career_dna_dimension: Mapped[str | None] = mapped_column(
        String(100), nullable=True,
    )
    source_experience: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    relevance_score: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.5,
    )
    order_index: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False,
    )

    # ── Relationships ──
    interview_prep: Mapped[InterviewPrep] = relationship(
        "InterviewPrep", back_populates="star_examples",
    )
    question: Mapped[InterviewQuestion | None] = relationship(
        "InterviewQuestion", back_populates="star_examples",
    )

    def __repr__(self) -> str:
        return (
            f"<STARExample(dimension={self.career_dna_dimension}, "
            f"relevance={self.relevance_score})>"
        )


# ── InterviewPreference ────────────────────────────────────────


class InterviewPreference(Base, UUIDMixin, TimestampMixin):
    """User preferences for Interview Intelligence™.

    Supports user autonomy (PathForge Manifesto #5):
    users control default preparation depth, maximum saved
    preps, and notification preferences.
    """

    __tablename__ = "interview_preferences"

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
    default_prep_depth: Mapped[str | None] = mapped_column(
        String(30), nullable=True,
    )
    max_saved_preps: Mapped[int] = mapped_column(
        Integer, default=50, server_default="50", nullable=False,
    )
    include_salary_negotiation: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )
    notification_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true", nullable=False,
    )

    # ── Relationships ──
    user: Mapped[User] = relationship("User")
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="interview_preference",
    )

    def __repr__(self) -> str:
        return (
            f"<InterviewPreference(user_id={self.user_id}, "
            f"max_saved_preps={self.max_saved_preps})>"
        )
