"""
PathForge — Career DNA Models
================================
Career DNA™ domain models representing the 6 dimensions
of career intelligence.

Dimensions:
    1. SkillGenome — Comprehensive skill map (explicit + hidden)
    2. ExperienceBlueprint — Career experience pattern analysis
    3. GrowthVector — Career trajectory projection
    4. ValuesProfile — Career values and alignment
    5. MarketPosition — Real-time market standing
    6. HiddenSkill — AI-discovered transferable competency
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.career_action_planner import (
        CareerActionPlan,
        CareerActionPlannerPreference,
    )
    from app.models.career_passport import (
        CareerPassportPreference,
        CountryComparison,
        CredentialMapping,
        MarketDemandEntry,
        VisaAssessment,
    )
    from app.models.career_simulation import (
        CareerSimulation,
        SimulationPreference,
    )
    from app.models.collective_intelligence import (
        CareerPulseEntry,
        CollectiveIntelligencePreference,
        IndustrySnapshot,
        PeerCohortAnalysis,
    )
    from app.models.collective_intelligence import (
        SalaryBenchmark as CISalaryBenchmark,
    )
    from app.models.hidden_job_market import (
        CompanySignal,
        HiddenJobMarketPreference,
    )
    from app.models.interview_intelligence import (
        InterviewPreference,
        InterviewPrep,
    )
    from app.models.predictive_career import (
        CareerForecast,
        DisruptionForecast,
        EmergingRole,
        OpportunitySurface,
        PredictiveCareerPreference,
    )
    from app.models.salary_intelligence import (
        SalaryEstimate,
        SalaryHistoryEntry,
        SalaryPreference,
        SalaryScenario,
        SkillSalaryImpact,
    )
    from app.models.skill_decay import (
        MarketDemandSnapshot,
        ReskillingPathway,
        SkillDecayPreference,
        SkillFreshness,
        SkillVelocityEntry,
    )
    from app.models.threat_radar import (
        AlertPreference,
        AutomationRisk,
        CareerResilienceSnapshot,
        IndustryTrend,
        SkillShieldEntry,
        ThreatAlert,
    )
    from app.models.transition_pathways import (
        TransitionPath,
        TransitionPreference,
    )
    from app.models.user import User

# ── Enums ──────────────────────────────────────────────────────


class SkillSource(enum.StrEnum):
    """How a skill was identified."""

    EXPLICIT = "explicit"
    INFERRED = "inferred"
    MARKET_VALIDATED = "market_validated"


class SkillCategory(enum.StrEnum):
    """High-level skill classification."""

    TECHNICAL = "technical"
    SOFT = "soft"
    LANGUAGE = "language"
    TOOL = "tool"
    DOMAIN = "domain"


class ProficiencyLevel(enum.StrEnum):
    """Standardized proficiency rating."""

    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class CareerDirection(enum.StrEnum):
    """Career trajectory direction classification."""

    ASCENDING = "ascending"
    LATERAL = "lateral"
    TRANSITIONING = "transitioning"
    EXPLORING = "exploring"


class TrajectoryStatus(enum.StrEnum):
    """Growth trajectory status."""

    ACCELERATING = "accelerating"
    STEADY = "steady"
    PLATEAUING = "plateauing"
    PIVOTING = "pivoting"


class WorkStyle(enum.StrEnum):
    """Work style preference."""

    AUTONOMOUS = "autonomous"
    COLLABORATIVE = "collaborative"
    STRUCTURED = "structured"
    FLEXIBLE = "flexible"


class ImpactPreference(enum.StrEnum):
    """Preferred scope of impact."""

    INDIVIDUAL = "individual"
    TEAM = "team"
    ORGANIZATIONAL = "organizational"
    SOCIETAL = "societal"


class MarketTrend(enum.StrEnum):
    """Market demand trend direction."""

    RISING = "rising"
    STABLE = "stable"
    DECLINING = "declining"


class DiscoveryMethod(enum.StrEnum):
    """How a hidden skill was discovered."""

    RESUME_INFERENCE = "resume_inference"
    MARKET_CROSSREF = "market_crossref"


# ── Career DNA Hub ─────────────────────────────────────────────


class CareerDNA(UUIDMixin, TimestampMixin, Base):
    """
    Hub entity linking a user to their living Career DNA™ profile.

    One profile per user. Auto-recomputed on data changes.
    Version-tracked for diff history.
    """

    __tablename__ = "career_dna"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    completeness_score: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    last_analysis_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Profile context (populated during Career DNA analysis)
    primary_industry: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    primary_role: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    location: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    seniority_level: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )

    # Relationships
    user: Mapped[User] = relationship(
        "User", back_populates="career_dna"
    )
    skill_genome: Mapped[list[SkillGenomeEntry]] = relationship(
        "SkillGenomeEntry", back_populates="career_dna", cascade="all, delete-orphan"
    )
    hidden_skills: Mapped[list[HiddenSkill]] = relationship(
        "HiddenSkill", back_populates="career_dna", cascade="all, delete-orphan"
    )
    experience_blueprint: Mapped[ExperienceBlueprint | None] = relationship(
        "ExperienceBlueprint",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )
    growth_vector: Mapped[GrowthVector | None] = relationship(
        "GrowthVector",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )
    values_profile: Mapped[ValuesProfile | None] = relationship(
        "ValuesProfile",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )
    market_position: Mapped[MarketPosition | None] = relationship(
        "MarketPosition",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Career Threat Radar™ relationships
    automation_risk: Mapped[AutomationRisk | None] = relationship(
        "AutomationRisk",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )
    industry_trends: Mapped[list[IndustryTrend]] = relationship(
        "IndustryTrend",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    skill_shield_entries: Mapped[list[SkillShieldEntry]] = relationship(
        "SkillShieldEntry",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    resilience_snapshots: Mapped[list[CareerResilienceSnapshot]] = relationship(
        "CareerResilienceSnapshot",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    threat_alerts: Mapped[list[ThreatAlert]] = relationship(
        "ThreatAlert",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    alert_preference: Mapped[AlertPreference | None] = relationship(
        "AlertPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Skill Decay & Growth Tracker™ relationships
    skill_freshness: Mapped[list[SkillFreshness]] = relationship(
        "SkillFreshness",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    market_demand_snapshots: Mapped[list[MarketDemandSnapshot]] = relationship(
        "MarketDemandSnapshot",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    skill_velocity_entries: Mapped[list[SkillVelocityEntry]] = relationship(
        "SkillVelocityEntry",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    reskilling_pathways: Mapped[list[ReskillingPathway]] = relationship(
        "ReskillingPathway",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    decay_preference: Mapped[SkillDecayPreference | None] = relationship(
        "SkillDecayPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Salary Intelligence Engine™ relationships
    salary_estimates: Mapped[list[SalaryEstimate]] = relationship(
        "SalaryEstimate",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    skill_salary_impacts: Mapped[list[SkillSalaryImpact]] = relationship(
        "SkillSalaryImpact",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    salary_history: Mapped[list[SalaryHistoryEntry]] = relationship(
        "SalaryHistoryEntry",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    salary_scenarios: Mapped[list[SalaryScenario]] = relationship(
        "SalaryScenario",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    salary_preference: Mapped[SalaryPreference | None] = relationship(
        "SalaryPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Transition Pathways relationships
    transition_paths: Mapped[list[TransitionPath]] = relationship(
        "TransitionPath",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    transition_preference: Mapped[TransitionPreference | None] = relationship(
        "TransitionPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Career Simulation Engine™ relationships
    simulations: Mapped[list[CareerSimulation]] = relationship(
        "CareerSimulation",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    simulation_preference: Mapped[SimulationPreference | None] = relationship(
        "SimulationPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Interview Intelligence™ relationships
    interview_preps: Mapped[list[InterviewPrep]] = relationship(
        "InterviewPrep",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    interview_preference: Mapped[InterviewPreference | None] = relationship(
        "InterviewPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Hidden Job Market Detector™ relationships
    company_signals: Mapped[list[CompanySignal]] = relationship(
        "CompanySignal",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    hidden_job_market_preference: Mapped[HiddenJobMarketPreference | None] = relationship(
        "HiddenJobMarketPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Cross-Border Career Passport™ relationships
    credential_mappings: Mapped[list[CredentialMapping]] = relationship(
        "CredentialMapping",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    country_comparisons: Mapped[list[CountryComparison]] = relationship(
        "CountryComparison",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    visa_assessments: Mapped[list[VisaAssessment]] = relationship(
        "VisaAssessment",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    passport_market_demand: Mapped[list[MarketDemandEntry]] = relationship(
        "MarketDemandEntry",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    career_passport_preference: Mapped[CareerPassportPreference | None] = relationship(
        "CareerPassportPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Collective Intelligence Engine™ relationships
    industry_snapshots: Mapped[list[IndustrySnapshot]] = relationship(
        "IndustrySnapshot",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    ci_salary_benchmarks: Mapped[list[CISalaryBenchmark]] = relationship(
        "SalaryBenchmark",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    peer_cohort_analyses: Mapped[list[PeerCohortAnalysis]] = relationship(
        "PeerCohortAnalysis",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    career_pulse_entries: Mapped[list[CareerPulseEntry]] = relationship(
        "CareerPulseEntry",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    ci_preference: Mapped[CollectiveIntelligencePreference | None] = relationship(
        "CollectiveIntelligencePreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Predictive Career Engine™ relationships
    emerging_roles: Mapped[list[EmergingRole]] = relationship(
        "EmergingRole",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    disruption_forecasts: Mapped[list[DisruptionForecast]] = relationship(
        "DisruptionForecast",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    opportunity_surfaces: Mapped[list[OpportunitySurface]] = relationship(
        "OpportunitySurface",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    career_forecasts: Mapped[list[CareerForecast]] = relationship(
        "CareerForecast",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    predictive_career_preference: Mapped[PredictiveCareerPreference | None] = relationship(
        "PredictiveCareerPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    # Career Action Planner™ relationships
    career_action_plans: Mapped[list[CareerActionPlan]] = relationship(
        "CareerActionPlan",
        back_populates="career_dna",
        cascade="all, delete-orphan",
    )
    career_action_planner_preference: Mapped[CareerActionPlannerPreference | None] = relationship(
        "CareerActionPlannerPreference",
        back_populates="career_dna",
        uselist=False,
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<CareerDNA user={self.user_id} v{self.version}>"


# ── Dimension 1: Skill Genome ──────────────────────────────────


class SkillGenomeEntry(UUIDMixin, TimestampMixin, Base):
    """
    Individual skill within the Career DNA genome.

    Richer than the base Skill model — includes source tracking,
    confidence scoring, and evidence chains for explainability.
    """

    __tablename__ = "skill_genome_entries"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(
        String(50), default=SkillCategory.TECHNICAL.value, nullable=False
    )
    proficiency_level: Mapped[str] = mapped_column(
        String(50), default=ProficiencyLevel.INTERMEDIATE.value, nullable=False
    )
    source: Mapped[str] = mapped_column(
        String(50), default=SkillSource.EXPLICIT.value, nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    years_experience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    last_used_date: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="skill_genome"
    )

    def __repr__(self) -> str:
        return f"<SkillGenomeEntry {self.skill_name} ({self.source})>"


# ── Dimension 6: Hidden Skills ─────────────────────────────────


class HiddenSkill(UUIDMixin, TimestampMixin, Base):
    """
    AI-discovered transferable skill not explicitly listed by the user.

    Dual-source discovery:
        A) LLM semantic inference from experience descriptions
        B) Market cross-reference from job listing skill frequency

    User can confirm or reject (human-in-the-loop).
    """

    __tablename__ = "hidden_skills"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    skill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    discovery_method: Mapped[str] = mapped_column(
        String(50), default=DiscoveryMethod.RESUME_INFERENCE.value, nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    evidence: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    user_confirmed: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    source_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="hidden_skills"
    )

    def __repr__(self) -> str:
        return f"<HiddenSkill {self.skill_name} ({self.discovery_method})>"


# ── Dimension 2: Experience Blueprint ──────────────────────────


class ExperienceBlueprint(UUIDMixin, TimestampMixin, Base):
    """
    Analyzed career experience pattern.

    Examines career timeline, role transitions, tenure patterns,
    and industry diversity to classify career direction.
    """

    __tablename__ = "experience_blueprints"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    total_years: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    role_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    avg_tenure_months: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    career_direction: Mapped[str] = mapped_column(
        String(50), default=CareerDirection.EXPLORING.value, nullable=False
    )
    industry_diversity: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    seniority_trajectory: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    pattern_analysis: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="experience_blueprint"
    )

    def __repr__(self) -> str:
        return f"<ExperienceBlueprint dir={self.career_direction}>"


# ── Dimension 3: Growth Vector ─────────────────────────────────


class GrowthVector(UUIDMixin, TimestampMixin, Base):
    """
    Career trajectory projection.

    Multi-signal computation combining:
        - Skill trajectory (demand vs. proficiency)
        - Market demand curves
        - Experience velocity and progression pattern
    """

    __tablename__ = "growth_vectors"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    current_trajectory: Mapped[str] = mapped_column(
        String(50), default=TrajectoryStatus.STEADY.value, nullable=False
    )
    projected_roles: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    skill_velocity: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    growth_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    analysis_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Sprint 36 WS-6 / Audit F25: User-editable target role
    target_role: Mapped[str | None] = mapped_column(
        String(255), nullable=True, doc="User-set career target role"
    )

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="growth_vector"
    )

    def __repr__(self) -> str:
        return f"<GrowthVector trajectory={self.current_trajectory}>"


# ── Dimension 4: Values Profile ────────────────────────────────


class ValuesProfile(UUIDMixin, TimestampMixin, Base):
    """
    Career values and alignment preferences.

    4-dimensional model derived from experience patterns
    and stated preferences — never from demographic data.
    Based on Theory of Work Adjustment (TWA) framework.
    """

    __tablename__ = "values_profiles"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    work_style: Mapped[str] = mapped_column(
        String(50), default=WorkStyle.FLEXIBLE.value, nullable=False
    )
    impact_preference: Mapped[str] = mapped_column(
        String(50), default=ImpactPreference.TEAM.value, nullable=False
    )
    environment_fit: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    derived_values: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="values_profile"
    )

    def __repr__(self) -> str:
        return f"<ValuesProfile style={self.work_style}>"


# ── Dimension 5: Market Position ───────────────────────────────


class MarketPosition(UUIDMixin, TimestampMixin, Base):
    """
    Real-time market standing snapshot.

    Computed from PathForge's own job listing data —
    skill demand frequency, matching job count, trend direction.
    """

    __tablename__ = "market_positions"

    career_dna_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("career_dna.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    percentile_overall: Mapped[float] = mapped_column(
        Float, default=50.0, nullable=False
    )
    skill_demand_scores: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    matching_job_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    market_trend: Mapped[str] = mapped_column(
        String(50), default=MarketTrend.STABLE.value, nullable=False
    )
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=func.now(),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    career_dna: Mapped[CareerDNA] = relationship(
        "CareerDNA", back_populates="market_position"
    )

    def __repr__(self) -> str:
        return f"<MarketPosition pct={self.percentile_overall}>"
