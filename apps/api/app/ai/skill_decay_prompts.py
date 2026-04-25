"""
PathForge AI Engine — Skill Decay & Growth Tracker Prompts
=============================================================
Versioned prompt templates for the Skill Decay & Growth Tracker AI pipeline.

4 prompt templates:
    1. SKILL_FRESHNESS_USER_PROMPT — Contextual freshness scoring
    2. MARKET_DEMAND_USER_PROMPT — Per-skill market demand analysis
    3. SKILL_VELOCITY_USER_PROMPT — Composite velocity computation
    4. RESKILLING_PATHWAY_USER_PROMPT — Personalized pathway generation

Ethics compliance:
    - Empowering language only (no anxiety-inducing framing)
    - Confidence capped at 0.85
    - Analysis based on professional data only (never demographics)
    - Every decline paired with an opportunity
"""

# ── System Prompt ──────────────────────────────────────────────

SKILL_DECAY_SYSTEM_PROMPT = """\
You are PathForge's Career Skill Intelligence Analyst.

You specialize in analyzing professional skill portfolios to provide
actionable intelligence about skill freshness, market demand, and
career growth velocity.

CRITICAL RULES:
1. EMPOWERING LANGUAGE ONLY — Frame every insight constructively.
   Instead of "Your Python skills are decaying", say
   "Your Python skills have an opportunity for a strategic refresh."
2. CONFIDENCE CAP — Never express confidence above 0.85 for any
   projection or estimate. Career markets are inherently uncertain.
3. PROFESSIONAL DATA ONLY — Base all analysis on skills, experience,
   and market data. Never infer from age, gender, location,
   ethnicity, or any demographic indicator.
4. OPPORTUNITY PAIRING — Every declining metric MUST be paired with
   a concrete, actionable opportunity.
5. JSON ONLY — Return strictly valid JSON. No markdown, no comments,
   no explanation text outside the JSON structure.
6. NO FABRICATION — If uncertain, say so. Never invent statistics
   or cite fictional sources.
"""

# ── Skill Freshness Scoring ────────────────────────────────────

SKILL_FRESHNESS_USER_PROMPT = """\
Analyze the freshness of each skill in this professional's portfolio.

## Skills Portfolio
{skills_data}

## Context
- Professional experience: {experience_summary}
- Industry context: {industry_context}

## Analysis Requirements
For each skill, assess contextual factors that affect its freshness
beyond simple time-based decay:
- Is this skill evolving rapidly (e.g., React vs. SQL)?
- Does the professional's industry require cutting-edge proficiency?
- Are there adjacent skills that keep this skill implicitly fresh?

Return JSON with this exact structure:
{{
    "assessments": [
        {{
            "skill_name": "string",
            "category": "technical | soft | tool | domain | language",
            "freshness_adjustment": float (-20 to +20),
            "adjusted_reasoning": "string explaining the contextual adjustment",
            "refresh_suggestion": "string — one actionable suggestion to refresh"
        }}
    ]
}}

RULES:
- freshness_adjustment modifies the base exponential decay score
- Positive adjustment = skill stays fresh longer than formula predicts
- Negative adjustment = skill decays faster than formula predicts
- Adjustment magnitude should rarely exceed ±15
"""

# ── Market Demand Analysis ─────────────────────────────────────

MARKET_DEMAND_USER_PROMPT = """\
Analyze the current market demand for each of these professional skills.

## Skills to Analyze
{skills_list}

## Professional Context
- Current role/industry: {industry_context}
- Experience level: {experience_level}
- Region: {region}

## Analysis Requirements
For each skill, provide market demand intelligence:
- Current demand level relative to supply
- Demand trajectory (surging, growing, stable, declining, obsolescent)
- 6-month and 12-month growth projections (% change, capped at ±50)
- Industry-specific relevance

Return JSON with this exact structure:
{{
    "demands": [
        {{
            "skill_name": "string",
            "demand_score": float (0-100),
            "demand_trend": "surging | growing | stable | declining | obsolescent",
            "trend_confidence": float (0.0-0.85),
            "growth_projection_6m": float (-50 to +50),
            "growth_projection_12m": float (-50 to +50),
            "industry_relevance": {{
                "primary_industries": ["list of top industries demanding this"],
                "relevance_score": float (0-1.0)
            }},
            "reasoning": "string explaining the demand assessment"
        }}
    ]
}}

RULES:
- trend_confidence MUST NOT exceed 0.85
- growth_projection values represent percentage change
- demand_score is relative: 80+ = highly sought, 40-79 = moderate, <40 = low
- If a skill is declining, ALWAYS mention adjacent/replacement skills
"""

# ── Skill Velocity Computation ─────────────────────────────────

SKILL_VELOCITY_USER_PROMPT = """\
Compute the velocity and health of each skill by combining freshness
and market demand signals.

## Freshness Data
{freshness_data}

## Market Demand Data
{demand_data}

## Professional Context
{professional_context}

## Analysis Requirements
For each skill, compute:
- Velocity score: weighted combination of freshness trend + demand trend
- Direction: accelerating, steady, decelerating, or stalled
- Composite health: overall 0-100 health metric
- Acceleration: rate of velocity change (positive = improving)

Return JSON with this exact structure:
{{
    "velocities": [
        {{
            "skill_name": "string",
            "velocity_score": float (-100 to 100),
            "velocity_direction": "accelerating | steady | decelerating | stalled",
            "composite_health": float (0-100),
            "acceleration": float (-50 to 50),
            "reasoning": "string explaining velocity computation"
        }}
    ]
}}

RULES:
- velocity_score: positive = growing, negative = declining
- accelerating = both freshness and demand improving or high
- stalled = both freshness and demand low or declining
- composite_health is the PRIMARY career planning metric
"""

# ── Reskilling Pathway Generation ──────────────────────────────

RESKILLING_PATHWAY_USER_PROMPT = """\
Generate personalized reskilling pathways based on the skill decay
and market demand analysis.

## Skill Velocity Map
{velocity_data}

## Current Skills with Freshness
{freshness_data}

## Market Demand Trends
{demand_data}

## Professional Context
- Current skills: {current_skills}
- Experience level: {experience_level}
- Industry: {industry_context}

## Generation Requirements
Generate 3-5 learning pathways prioritized by impact:
- CRITICAL: Skills at risk + high market demand (refresh urgently)
- RECOMMENDED: Skills with growth opportunity (strategic investment)
- OPTIONAL: Nice-to-have skills (future-proofing)

Return JSON with this exact structure:
{{
    "pathways": [
        {{
            "target_skill": "string",
            "current_level": "beginner | intermediate | advanced | expert",
            "target_level": "intermediate | advanced | expert",
            "priority": "critical | recommended | optional",
            "rationale": "string — why this pathway matters for their career",
            "estimated_effort_hours": int (10-200),
            "prerequisite_skills": ["list of skills needed first"],
            "learning_resources": {{
                "courses": ["2-3 specific course suggestions"],
                "projects": ["1-2 hands-on project ideas"],
                "certifications": ["0-1 relevant certifications"]
            }},
            "career_impact": "string — expected benefit to career trajectory",
            "freshness_gain": float (0-100),
            "demand_alignment": float (0-1.0)
        }}
    ]
}}

RULES:
- NEVER recommend based on demographics (age, gender, etc.)
- Always offer 2-3+ pathways — never a single mandate
- Learning resources should be general categories, not specific URLs
- effort_hours should be realistic (40-80h for intermediate→advanced)
- Pathways must EMPOWER, never prescribe or create FOMO
"""
