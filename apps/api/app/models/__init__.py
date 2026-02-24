"""
PathForge — Models Package
===========================
Central import point for all SQLAlchemy models.
Alembic auto-generates migrations from these imports.
"""

from app.models.ai_transparency import AITransparencyRecord
from app.models.analytics import CVExperiment, FunnelEvent, MarketInsight
from app.models.application import Application, CVVersion
from app.models.base import Base
from app.models.career_action_planner import (
    CareerActionPlan,
    CareerActionPlannerPreference,
    MilestoneProgress,
    PlanMilestone,
    PlanRecommendation,
)
from app.models.career_command_center import (
    CareerSnapshot,
    CommandCenterPreference,
)
from app.models.career_dna import (
    CareerDNA,
    ExperienceBlueprint,
    GrowthVector,
    HiddenSkill,
    MarketPosition,
    SkillGenomeEntry,
    ValuesProfile,
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
    SimulationInput,
    SimulationOutcome,
    SimulationPreference,
    SimulationRecommendation,
)
from app.models.collective_intelligence import (
    CareerPulseEntry,
    CollectiveIntelligencePreference,
    IndustrySnapshot,
    PeerCohortAnalysis,
    SalaryBenchmark,
)
from app.models.hidden_job_market import (
    CompanySignal,
    HiddenJobMarketPreference,
    HiddenOpportunity,
    OutreachTemplate,
    SignalMatchResult,
)
from app.models.interview_intelligence import (
    CompanyInsight,
    InterviewPreference,
    InterviewPrep,
    InterviewQuestion,
    STARExample,
)
from app.models.matching import JobListing, MatchResult
from app.models.notification import (
    CareerNotification,
    NotificationDigest,
    NotificationPreference,
)
from app.models.predictive_career import (
    CareerForecast,
    DisruptionForecast,
    EmergingRole,
    OpportunitySurface,
    PredictiveCareerPreference,
)
from app.models.preference import BlacklistEntry, Preference
from app.models.resume import Resume, Skill
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
    SkillBridgeEntry,
    TransitionComparison,
    TransitionMilestone,
    TransitionPath,
    TransitionPreference,
)
from app.models.user import User
from app.models.user_profile import DataExportRequest, UserProfile

__all__ = [
    "AITransparencyRecord",
    "AlertPreference",
    "Application",
    "AutomationRisk",
    "Base",
    "BlacklistEntry",
    "CVExperiment",
    "CVVersion",
    "CareerActionPlan",
    "CareerActionPlannerPreference",
    "CareerDNA",
    "CareerForecast",
    "CareerNotification",
    "CareerPassportPreference",
    "CareerPulseEntry",
    "CareerResilienceSnapshot",
    "CareerSimulation",
    "CareerSnapshot",
    "CollectiveIntelligencePreference",
    "CommandCenterPreference",
    "CompanyInsight",
    "CompanySignal",
    "CountryComparison",
    "CredentialMapping",
    "DataExportRequest",
    "DisruptionForecast",
    "EmergingRole",
    "ExperienceBlueprint",
    "FunnelEvent",
    "GrowthVector",
    "HiddenJobMarketPreference",
    "HiddenOpportunity",
    "HiddenSkill",
    "IndustrySnapshot",
    "IndustryTrend",
    "InterviewPreference",
    "InterviewPrep",
    "InterviewQuestion",
    "JobListing",
    "MarketDemandEntry",
    "MarketDemandSnapshot",
    "MarketInsight",
    "MarketPosition",
    "MatchResult",
    "MilestoneProgress",
    "NotificationDigest",
    "NotificationPreference",
    "OpportunitySurface",
    "OutreachTemplate",
    "PeerCohortAnalysis",
    "PlanMilestone",
    "PlanRecommendation",
    "PredictiveCareerPreference",
    "Preference",
    "ReskillingPathway",
    "Resume",
    "STARExample",
    "SalaryBenchmark",
    "SalaryEstimate",
    "SalaryHistoryEntry",
    "SalaryPreference",
    "SalaryScenario",
    "SignalMatchResult",
    "SimulationInput",
    "SimulationOutcome",
    "SimulationPreference",
    "SimulationRecommendation",
    "Skill",
    "SkillBridgeEntry",
    "SkillDecayPreference",
    "SkillFreshness",
    "SkillGenomeEntry",
    "SkillSalaryImpact",
    "SkillShieldEntry",
    "SkillVelocityEntry",
    "ThreatAlert",
    "TransitionComparison",
    "TransitionMilestone",
    "TransitionPath",
    "TransitionPreference",
    "User",
    "UserProfile",
    "ValuesProfile",
    "VisaAssessment",
]
